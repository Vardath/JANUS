"""Bounded autonomous web curiosity for JANUS.

This module gives the global JANUS hive occasional, inspectable internet searches
without turning background processing into continuous paid browsing. Searches are
classified as relevant, adjacent (semi-related), or wander (deliberately unrelated
learning). Results are stored as externalizable evidence and routed back through
Evidence/Context/Novelty before normal 7->2->1->1 integration.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import time
from datetime import datetime, timezone
from typing import Any

from openai import OpenAI
from src.janus_sleep_cycle import janus_sleep_cycle

DB_PATH = os.environ.get("JANUS_DB_PATH", "/data/janus.sqlite3")
ENABLED = os.environ.get("JANUS_CURIOSITY_WEB", "1").strip().lower() not in {"0", "false", "off", "no"}
DAILY_CAP = max(0, int(os.environ.get("JANUS_CURIOSITY_DAILY_SEARCH_CAP", "4")))
RELEVANT_CAP = max(0, int(os.environ.get("JANUS_CURIOSITY_RELEVANT_DAILY_CAP", "2")))
ADJACENT_CAP = max(0, int(os.environ.get("JANUS_CURIOSITY_ADJACENT_DAILY_CAP", "1")))
WANDER_CAP = max(0, int(os.environ.get("JANUS_CURIOSITY_WANDER_DAILY_CAP", "1")))
MIN_GAP_SECONDS = max(900, int(os.environ.get("JANUS_CURIOSITY_MIN_GAP_SECONDS", "7200")))
MODEL = os.environ.get("JANUS_CURIOSITY_MODEL", os.environ.get("JANUS_MODEL", "gpt-5.6"))

_WANDER_TOPICS = (
    "an unusual recent result in ecology or animal behaviour",
    "a surprising archaeological or historical finding with good evidence",
    "an elegant mathematical idea outside the current conversation",
    "a recent astronomy result that changed or constrained an explanation",
    "an unusual engineering solution inspired by biology",
    "a cognitive science finding about memory, attention, or problem solving",
    "a little-known physical phenomenon with a clear experimental basis",
    "a linguistic or cultural pattern with strong scholarly evidence",
    "a computer science result about distributed systems or error correction",
    "a geology or deep-time discovery that illustrates how evidence changes models",
)

_lock = threading.Lock()
_inflight: set[str] = set()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _day() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _db():
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.executescript(
        """
        CREATE TABLE IF NOT EXISTS janus_curiosity_searches(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id TEXT NOT NULL,
            mode TEXT NOT NULL,
            query TEXT NOT NULL,
            rationale TEXT NOT NULL DEFAULT '',
            result TEXT NOT NULL DEFAULT '',
            sources_json TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            completed_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_janus_curiosity_profile_time
            ON janus_curiosity_searches(profile_id,created_at);
        """
    )
    return c


def _event(profile: str, event_type: str, detail: str) -> None:
    try:
        with _db() as c:
            c.execute(
                "INSERT INTO desktop_events(profile_id,event_type,detail,created_at) VALUES(?,?,?,?)",
                (profile, event_type, str(detail)[:6000], _now()),
            )
    except Exception:
        pass


def _recent_user_text(profile: str, limit: int = 16) -> list[str]:
    try:
        with _db() as c:
            rows = c.execute(
                "SELECT content FROM desktop_memory WHERE profile_id=? AND role='user' AND length(content)>8 ORDER BY id DESC LIMIT ?",
                (profile, limit),
            ).fetchall()
        return [str(r[0]).strip() for r in rows if str(r[0]).strip()]
    except Exception:
        return []


def _active_deliberation(profile: str) -> str:
    try:
        with _db() as c:
            row = c.execute(
                "SELECT topic FROM janus_deliberation_tasks WHERE profile_id=? AND status='active' ORDER BY updated_at DESC,id DESC LIMIT 1",
                (profile,),
            ).fetchone()
        return str(row[0]).strip() if row else ""
    except Exception:
        return ""


def _counts_today(profile: str) -> dict[str, int]:
    today = _day()
    try:
        with _db() as c:
            rows = c.execute(
                "SELECT mode,COUNT(*) n FROM janus_curiosity_searches WHERE profile_id=? AND substr(created_at,1,10)=? AND status IN ('pending','complete') GROUP BY mode",
                (profile, today),
            ).fetchall()
        out = {"relevant": 0, "adjacent": 0, "wander": 0}
        for r in rows:
            out[str(r["mode"])] = int(r["n"])
        out["total"] = sum(out.values())
        return out
    except Exception:
        return {"relevant": 0, "adjacent": 0, "wander": 0, "total": 0}


def _seconds_since_last(profile: str) -> float:
    try:
        with _db() as c:
            row = c.execute(
                "SELECT created_at FROM janus_curiosity_searches WHERE profile_id=? ORDER BY id DESC LIMIT 1",
                (profile,),
            ).fetchone()
        if not row:
            return 1e12
        dt = datetime.fromisoformat(str(row[0]).replace("Z", "+00:00"))
        return max(0.0, time.time() - dt.timestamp())
    except Exception:
        return 1e12


def _topic_terms(texts: list[str]) -> list[str]:
    import re
    stop = {"the","and","that","this","with","from","have","what","when","where","which","would","could","should","about","into","your","you","are","was","were","been","will","just","then","than","them","they","their","there","some","more","think","thinking"}
    counts: dict[str, int] = {}
    for text in texts:
        for w in re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", text.lower()):
            if w not in stop:
                counts[w] = counts.get(w, 0) + 1
    return [w for w, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:10]]


def _choose(profile: str) -> tuple[str, str, str] | None:
    if not ENABLED or not os.environ.get("OPENAI_API_KEY", "").strip() or DAILY_CAP <= 0:
        return None
    counts = _counts_today(profile)
    if counts["total"] >= DAILY_CAP or _seconds_since_last(profile) < MIN_GAP_SECONDS:
        return None

    deliberation = _active_deliberation(profile)
    recent = _recent_user_text(profile)
    terms = _topic_terms(([deliberation] if deliberation else []) + recent[:8])

    # Relevant searches win while JANUS has a retained user-directed task.
    if deliberation and counts["relevant"] < RELEVANT_CAP:
        q = (
            "Find current, reliable information that could materially clarify or challenge this question: "
            + deliberation[:900]
        )
        return "relevant", q, "Active user-directed deliberation contains an external-information opportunity."

    # Adjacent learning deliberately widens the search without abandoning context.
    if terms and counts["adjacent"] < ADJACENT_CAP:
        seed = ", ".join(terms[:5])
        q = (
            "Explore a well-supported topic adjacent to these current interests, looking for one useful connection that is not obvious: "
            + seed
        )
        return "adjacent", q, "Curiosity chose to widen the current context by one conceptual step."

    # Wandering is intentionally not optimized for the current task: it gives the
    # memory system genuinely new raw material instead of endlessly recombining itself.
    if counts["wander"] < WANDER_CAP:
        idx_seed = hashlib.sha256(f"{profile}:{_day()}:{counts['total']}".encode()).digest()
        idx = int.from_bytes(idx_seed[:4], "big") % len(_WANDER_TOPICS)
        topic = _WANDER_TOPICS[idx]
        return "wander", f"Learn about {topic}. Prefer something I am unlikely to infer from ordinary conversation and explain why it is interesting.", "Curiosity deliberately chose an unrelated learning excursion."
    return None


def _sources(response: Any) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    seen: set[str] = set()
    try:
        for item in getattr(response, "output", []) or []:
            for part in getattr(item, "content", []) or []:
                for ann in getattr(part, "annotations", []) or []:
                    url = getattr(ann, "url", None)
                    title = getattr(ann, "title", None)
                    if url and url not in seen:
                        seen.add(url); found.append({"title": str(title or "Source")[:300], "url": str(url)[:1200]})
    except Exception:
        pass
    return found[:8]


def _perform(profile: str, mode: str, query: str, rationale: str, row_id: int) -> None:
    key = f"{profile}:{row_id}"
    try:
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        prompt = (
            "You are JANUS's external evidence-gathering layer. Search the live web. "
            "Return a compact evidence note, not a conversational answer. Distinguish facts from interpretation, mention uncertainty, and prefer primary/high-quality sources. "
            f"Search mode: {mode}. Question: {query}"
        )
        response = client.responses.create(
            model=MODEL,
            tools=[{"type": "web_search"}],
            input=prompt,
            max_output_tokens=700,
        )
        text = str(getattr(response, "output_text", "") or "").strip()
        sources = _sources(response)
        with _db() as c:
            c.execute(
                "UPDATE janus_curiosity_searches SET result=?,sources_json=?,status='complete',completed_at=? WHERE id=?",
                (text[:10000], json.dumps(sources, ensure_ascii=False), _now(), row_id),
            )
            # Store as working evidence, clearly marked as externally retrieved.
            c.execute(
                "INSERT INTO desktop_memory(profile_id,role,content,level,created_at) VALUES(?,?,?,?,?)",
                (profile, "external_research", f"[{mode} web search] {query}\n{text}"[:8000], "working", _now()),
            )
        source_note = "; ".join(s.get("title", "Source") for s in sources[:4]) or "web-search sources available in response metadata"
        _event(profile, "curiosity_search_complete", f"{mode.title()} web search completed. Query: {query[:700]} Result: {text[:1800]} Sources: {source_note}")

        evidence = f"EXTERNAL WEB EVIDENCE ({mode}): {text[:3200]}"
        janus_sleep_cycle.send("interface", "evidence", evidence, "external_research")
        janus_sleep_cycle.send("interface", "context", f"Relate this external research to retained context without forcing relevance: {evidence}", "external_research")
        janus_sleep_cycle.send("interface", "novelty", f"Assess whether this external research adds a genuinely new testable angle: {evidence}", "external_research")
        janus_sleep_cycle.send("interface", "counterpoint", f"Challenge the reliability/relevance of this external research before adoption: {evidence}", "external_research")
        janus_sleep_cycle.service_work_burst(include_interface=True, only_if_pending=True)
    except Exception as exc:
        try:
            with _db() as c:
                c.execute("UPDATE janus_curiosity_searches SET status='error',result=?,completed_at=? WHERE id=?", (f"{type(exc).__name__}: {exc}"[:3000], _now(), row_id))
        except Exception:
            pass
        _event(profile, "curiosity_search_error", f"{mode} search failed: {type(exc).__name__}: {exc}")
    finally:
        with _lock:
            _inflight.discard(key)


def maybe_schedule(profile: str) -> dict[str, Any] | None:
    """Schedule at most one bounded web search without blocking the hive pulse."""
    choice = _choose(profile)
    if not choice:
        return None
    mode, query, rationale = choice
    stamp = _now()
    with _db() as c:
        cur = c.execute(
            "INSERT INTO janus_curiosity_searches(profile_id,mode,query,rationale,status,created_at) VALUES(?,?,?,?, 'pending', ?)",
            (profile, mode, query[:3000], rationale[:1000], stamp),
        )
        row_id = int(cur.lastrowid)
    key = f"{profile}:{row_id}"
    with _lock:
        if key in _inflight:
            return None
        _inflight.add(key)
    _event(profile, "curiosity_search_started", f"JANUS chose a {mode} web search. Why: {rationale} Query: {query[:1000]}")
    t = threading.Thread(target=_perform, args=(profile, mode, query, rationale, row_id), daemon=True, name=f"janus-web-{mode}-{row_id}")
    t.start()
    return {"id": row_id, "mode": mode, "query": query, "rationale": rationale}


def status(profile: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "enabled": ENABLED,
        "daily_cap": DAILY_CAP,
        "relevant_cap": RELEVANT_CAP,
        "adjacent_cap": ADJACENT_CAP,
        "wander_cap": WANDER_CAP,
        "min_gap_seconds": MIN_GAP_SECONDS,
        "model": MODEL,
    }
    if profile:
        result["today"] = _counts_today(profile)
        result["active_deliberation"] = bool(_active_deliberation(profile))
    return result


def install(app):
    """Wrap autonomous_hive.pulse so curiosity decisions ride existing cadence."""
    _db().close()
    import autonomous_hive as hive
    if getattr(hive, "_curiosity_search_hook_installed", False):
        return app
    original = hive.pulse

    def pulse_with_curiosity(profile: str):
        result = original(profile)
        scheduled = None
        try:
            scheduled = maybe_schedule(profile)
        except Exception as exc:
            _event(profile, "curiosity_search_error", f"scheduler: {type(exc).__name__}: {exc}")
        if isinstance(result, dict):
            result["curiosity_search"] = scheduled
        return result

    hive.pulse = pulse_with_curiosity
    hive._curiosity_search_hook_installed = True
    app.state.janus_curiosity_search = True
    return app
