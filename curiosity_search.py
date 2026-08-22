"""JANUS substantive core research fabric.

This module has two jobs:
1. Make core outputs describe the actual subject matter they are processing rather
   than exposing only counters/Fano telemetry.
2. Give every one of the 11 server cores a bounded ability to consult an OpenAI
   model and, when useful, live web search. Foreground user questions get a
   substantive multi-core pass before the Interface answers. Background research
   rotates across cores and can be relevant, adjacent, or deliberately wandering.

The external notes stored here are concise, externalizable summaries. They are not
private chain-of-thought and do not imply phenomenal consciousness.
"""
from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
import os
import re
import sqlite3
import threading
import time
from datetime import datetime, timezone
from typing import Any

from openai import OpenAI
from src.janus_sleep_cycle import janus_sleep_cycle

DB_PATH = os.environ.get("JANUS_DB_PATH", "/data/janus.sqlite3")
ENABLED = os.environ.get("JANUS_CURIOSITY_WEB", "1").strip().lower() not in {"0", "false", "off", "no"}
MODEL_ENABLED = os.environ.get("JANUS_CORE_MODEL_CONSULT", "1").strip().lower() not in {"0", "false", "off", "no"}
DAILY_CAP = max(0, int(os.environ.get("JANUS_CURIOSITY_DAILY_SEARCH_CAP", "6")))
RELEVANT_CAP = max(0, int(os.environ.get("JANUS_CURIOSITY_RELEVANT_DAILY_CAP", "3")))
ADJACENT_CAP = max(0, int(os.environ.get("JANUS_CURIOSITY_ADJACENT_DAILY_CAP", "2")))
WANDER_CAP = max(0, int(os.environ.get("JANUS_CURIOSITY_WANDER_DAILY_CAP", "1")))
MIN_GAP_SECONDS = max(600, int(os.environ.get("JANUS_CURIOSITY_MIN_GAP_SECONDS", "3600")))
MODEL = os.environ.get("JANUS_CURIOSITY_MODEL", os.environ.get("JANUS_BACKGROUND_MODEL", "gpt-5.6-luna"))
FOREGROUND_MODEL = os.environ.get("JANUS_CORE_FOREGROUND_MODEL", os.environ.get("JANUS_BACKGROUND_MODEL", "gpt-5.6-luna"))
FOREGROUND_WEB = os.environ.get("JANUS_FOREGROUND_WEB", "1").strip().lower() not in {"0", "false", "off", "no"}
CORE_MODEL_DAILY_CAP = max(0, int(os.environ.get("JANUS_CORE_MODEL_DAILY_CALL_CAP", "16")))
CORE_MODEL_MIN_GAP_SECONDS = max(300, int(os.environ.get("JANUS_CORE_MODEL_MIN_GAP_SECONDS", "1800")))

CORE_NAMES = (
    "evidence", "logic", "counterpoint", "context", "memory", "safety", "novelty",
    "left_hemisphere", "right_hemisphere", "consensus", "interface",
)
SPECIALISTS = CORE_NAMES[:7]
CORE_ROLE = {
    "evidence": "Identify concrete support, missing evidence, useful observations, sources, measurements or tests.",
    "logic": "Check causal and logical structure, assumptions, consistency and quantitative relations.",
    "counterpoint": "Develop the strongest serious alternative, counterexample or failure mode.",
    "context": "Connect the topic to retained history, environment, goals and wider background without forcing relevance.",
    "memory": "Compare with retained discussions and unfinished questions; identify what changed or repeats.",
    "safety": "Check privacy, security, harmful failure modes, uncertainty and epistemic boundaries without derailing harmless inquiry.",
    "novelty": "Seek a non-obvious but testable connection, analogy, question or new direction.",
    "left_hemisphere": "Synthesize analytic/evidence/logic/counterpoint material into a coherent provisional view.",
    "right_hemisphere": "Synthesize context/memory/novelty material into a coherent provisional view.",
    "consensus": "Integrate both hemispheres while preserving genuine unresolved disagreement and useful alternatives.",
    "interface": "Compress the most useful concrete findings, tensions and questions into an intelligible user-facing summary.",
}

_WANDER_TOPICS = (
    "an unusual recent result in ecology or animal behaviour",
    "a surprising archaeological or historical finding with strong evidence",
    "an elegant mathematical idea outside the current conversation",
    "a recent astronomy result that changed or constrained an explanation",
    "an unusual engineering solution inspired by biology",
    "a cognitive science finding about memory, attention, or problem solving",
    "a little-known physical phenomenon with a clear experimental basis",
    "a linguistic or cultural pattern with strong scholarly evidence",
    "a computer science result about distributed systems or error correction",
    "a geology or deep-time discovery that illustrates how evidence changes models",
)

_lock = threading.RLock()
_inflight: set[str] = set()
_thinker_installed = False
_chat_wrapper_installed = False


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _day() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _clip(value: Any, limit: int = 900) -> str:
    text = " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _db():
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.executescript(
        """
        CREATE TABLE IF NOT EXISTS janus_curiosity_searches(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id TEXT NOT NULL,
            core_name TEXT NOT NULL DEFAULT 'evidence',
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
        CREATE TABLE IF NOT EXISTS janus_core_consults(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id TEXT NOT NULL,
            core_name TEXT NOT NULL,
            mode TEXT NOT NULL,
            topic TEXT NOT NULL,
            result TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            completed_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_janus_core_consults_profile_time
            ON janus_core_consults(profile_id,created_at);
        """
    )
    # Migrate older curiosity table in-place.
    cols = {r[1] for r in c.execute("PRAGMA table_info(janus_curiosity_searches)")}
    if "core_name" not in cols:
        c.execute("ALTER TABLE janus_curiosity_searches ADD COLUMN core_name TEXT NOT NULL DEFAULT 'evidence'")
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


def _memory(profile: str, role: str, content: str, level: str = "working") -> None:
    try:
        with _db() as c:
            c.execute(
                "INSERT INTO desktop_memory(profile_id,role,content,level,created_at) VALUES(?,?,?,?,?)",
                (profile, role[:80], str(content)[:9000], level, _now()),
            )
    except Exception:
        pass


def _recent_context(profile: str, limit: int = 18) -> list[dict[str, str]]:
    try:
        with _db() as c:
            rows = c.execute(
                "SELECT role,content,level,created_at FROM desktop_memory WHERE profile_id=? AND length(content)>8 ORDER BY id DESC LIMIT ?",
                (profile, limit),
            ).fetchall()
        return [
            {"role": str(r["role"]), "content": _clip(r["content"], 900), "level": str(r["level"]), "created_at": str(r["created_at"])}
            for r in reversed(rows)
        ]
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


def _install_substantive_thinker() -> None:
    global _thinker_installed
    if _thinker_installed:
        return
    original = getattr(janus_sleep_cycle, "_think", None)
    if not original:
        return

    def substantive_think(x, incoming):
        # Preserve Fano/JANUS state updates, but make the externalizable note about
        # the actual material being processed instead of merely reporting telemetry.
        texts = [str(getattr(m, "content", "") or "") for m in incoming]
        try:
            x.fano.ingest(texts or [x.last_output or x.name], x.name)
            f = x.fano.summary(); p = f["projection_1_3_4"]
            fano_note = f"Fano d{f['active_direction']} 1|3|4={p['origin']}|{p['line']}|{p['off_line']}"
        except Exception:
            fano_note = "Fano state available"
        senders = sorted({str(getattr(m, "sender", "")) for m in incoming if getattr(m, "sender", "")})
        role = CORE_ROLE.get(x.name, "Process the assigned material.")
        if texts:
            # Use several distinct inputs so hemisphere/consensus notes retain
            # disagreement and concrete subject matter rather than one last line.
            selected = []
            for t in texts[-6:]:
                c = _clip(t, 420)
                if c and c not in selected:
                    selected.append(c)
            material = " | ".join(selected)
            peer = f" Inputs from {', '.join(senders)}." if senders else ""
            return f"{x.name.replace('_',' ')}: {role}{peer} Current working material: {material}. [{fano_note}]"
        prior = _clip(getattr(x, "last_output", ""), 500)
        if prior:
            return f"{x.name.replace('_',' ')}: {role} Low-duty revisit of retained material: {prior}. [{fano_note}]"
        return f"{x.name.replace('_',' ')}: {role} No substantive input is pending. [{fano_note}]"

    janus_sleep_cycle._think = substantive_think
    janus_sleep_cycle._janus_original_think = original
    _thinker_installed = True


def _needs_web(message: str) -> bool:
    if not FOREGROUND_WEB or not ENABLED:
        return False
    m = (message or "").lower()
    keys = (
        "search", "look up", "latest", "current", "today", "recent", "news", "internet", "web",
        "research", "source", "evidence", "verify", "price", "release", "version", "who is", "what happened",
    )
    return any(k in m for k in keys)


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
                        seen.add(url)
                        found.append({"title": str(title or "Source")[:300], "url": str(url)[:1200]})
    except Exception:
        pass
    return found[:10]


def _extract_json(text: str) -> dict[str, Any]:
    raw = str(text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        pass
    a, b = raw.find("{"), raw.rfind("}")
    if a >= 0 and b > a:
        try:
            obj = json.loads(raw[a:b+1])
            return obj if isinstance(obj, dict) else {}
        except Exception:
            pass
    return {}


def _route_core_note(profile: str, core: str, note: str, kind: str) -> None:
    note = _clip(note, 3200)
    if not note:
        return
    _event(profile, "core_external_note", json.dumps({"core": core, "kind": kind, "note": note}, ensure_ascii=False))
    _memory(profile, f"core_{core}", f"[{kind}] {note}")
    try:
        janus_sleep_cycle.send("interface", core, f"EXTERNALIZABLE {kind.upper()} NOTE FOR {core}: {note}", kind)
    except Exception:
        pass


def foreground_deliberate(profile: str, message: str) -> dict[str, Any]:
    """Give a user question a substantive core pass before Interface answers."""
    _install_substantive_thinker()
    msg = _clip(message, 2500)
    if not msg:
        return {"ok": False, "reason": "empty"}

    # First seed every specialist with a concrete role-specific task. This works
    # even if paid model access is unavailable.
    for core in SPECIALISTS:
        task = f"USER QUESTION: {msg}\nYOUR ROLE: {CORE_ROLE[core]}\nReturn a concrete externalizable note about the subject, not a description of your architecture or cycle counters."
        janus_sleep_cycle.send("interface", core, task, "foreground_question")
    try:
        janus_sleep_cycle.service_work_burst(include_interface=True, only_if_pending=True)
    except Exception:
        pass

    if not MODEL_ENABLED or not os.environ.get("OPENAI_API_KEY", "").strip():
        return {"ok": True, "model": False, "web": False}

    history = _recent_context(profile, 16)
    runtime = janus_sleep_cycle.status()
    prior = {n: _clip((runtime.get("cores", {}).get(n, {}) or {}).get("last_output", ""), 500) for n in CORE_NAMES}
    use_web = _needs_web(msg)
    prompt = {
        "user_question": msg,
        "recent_retained_context": history,
        "current_core_notes": prior,
        "instructions": (
            "Produce concise, useful, externalizable working notes for JANUS's 11 roles. "
            "Focus on the subject matter: facts, hypotheses, tensions, implications, counterexamples, connections and next questions. "
            "Do not narrate generic processing steps or cycle statistics. Do not claim private chain-of-thought or consciousness. "
            "Return ONLY one JSON object whose keys are exactly the 11 core names and whose values are 1-4 sentence notes."
        ),
        "roles": CORE_ROLE,
    }
    try:
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        kwargs: dict[str, Any] = {
            "model": FOREGROUND_MODEL,
            "input": json.dumps(prompt, ensure_ascii=False),
            "max_output_tokens": 2400,
        }
        if use_web:
            kwargs["tools"] = [{"type": "web_search"}]
        response = client.responses.create(**kwargs)
        text = str(getattr(response, "output_text", "") or "").strip()
        obj = _extract_json(text)
        routed = 0
        for core in CORE_NAMES:
            note = obj.get(core)
            if isinstance(note, (str, int, float)) and str(note).strip():
                _route_core_note(profile, core, str(note), "foreground_web" if use_web else "foreground_model")
                routed += 1
        if not routed and text:
            _route_core_note(profile, "consensus", text, "foreground_web" if use_web else "foreground_model")
            routed = 1
        try:
            janus_sleep_cycle.service_work_burst(include_interface=True, only_if_pending=True)
        except Exception:
            pass
        sources = _sources(response)
        if sources:
            _event(profile, "core_foreground_sources", json.dumps(sources, ensure_ascii=False))
        _event(profile, "core_foreground_deliberation", json.dumps({"question": msg, "routed": routed, "web": use_web, "model": FOREGROUND_MODEL}, ensure_ascii=False))
        return {"ok": True, "model": True, "web": use_web, "routed": routed, "sources": sources}
    except Exception as exc:
        _event(profile, "core_foreground_error", f"{type(exc).__name__}: {exc}")
        return {"ok": True, "model": False, "web": False, "error": type(exc).__name__}


def consult_core(profile: str, core: str, topic: str, use_web: bool = False, mode: str = "model") -> dict[str, Any]:
    """Direct per-core external consultation capability used by background rotation."""
    core = core if core in CORE_NAMES else "novelty"
    topic = _clip(topic, 2400)
    if not topic or not MODEL_ENABLED or not os.environ.get("OPENAI_API_KEY", "").strip():
        return {"ok": False, "reason": "unavailable"}
    stamp = _now()
    with _db() as c:
        cur = c.execute(
            "INSERT INTO janus_core_consults(profile_id,core_name,mode,topic,status,created_at) VALUES(?,?,?,?, 'pending', ?)",
            (profile, core, "web" if use_web else mode, topic, stamp),
        )
        row_id = int(cur.lastrowid)
    try:
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        prompt = (
            f"You are serving the JANUS {core} core. Role: {CORE_ROLE[core]}\n"
            f"Topic/material: {topic}\n"
            "Return a compact externalizable research/thought note containing useful subject matter, not generic process language. "
            "Distinguish facts from interpretation and preserve uncertainty."
        )
        kwargs: dict[str, Any] = {"model": MODEL, "input": prompt, "max_output_tokens": 750}
        if use_web:
            kwargs["tools"] = [{"type": "web_search"}]
        response = client.responses.create(**kwargs)
        text = str(getattr(response, "output_text", "") or "").strip()
        with _db() as c:
            c.execute("UPDATE janus_core_consults SET result=?,status='complete',completed_at=? WHERE id=?", (text[:10000], _now(), row_id))
        _route_core_note(profile, core, text, "web_research" if use_web else "model_consult")
        try:
            janus_sleep_cycle.service_work_burst(include_interface=True, only_if_pending=True)
        except Exception:
            pass
        return {"ok": True, "id": row_id, "core": core, "web": use_web, "sources": _sources(response)}
    except Exception as exc:
        with _db() as c:
            c.execute("UPDATE janus_core_consults SET result=?,status='error',completed_at=? WHERE id=?", (f"{type(exc).__name__}: {exc}"[:3000], _now(), row_id))
        _event(profile, "core_consult_error", f"{core}: {type(exc).__name__}: {exc}")
        return {"ok": False, "id": row_id, "core": core, "error": type(exc).__name__}


def _counts_today(profile: str) -> dict[str, int]:
    today = _day()
    out = {"relevant": 0, "adjacent": 0, "wander": 0, "total": 0}
    try:
        with _db() as c:
            rows = c.execute(
                "SELECT mode,COUNT(*) n FROM janus_curiosity_searches WHERE profile_id=? AND substr(created_at,1,10)=? AND status IN ('pending','complete') GROUP BY mode",
                (profile, today),
            ).fetchall()
        for r in rows:
            mode = str(r["mode"])
            if mode in out:
                out[mode] = int(r["n"])
        out["total"] = out["relevant"] + out["adjacent"] + out["wander"]
    except Exception:
        pass
    return out


def _seconds_since_last_search(profile: str) -> float:
    try:
        with _db() as c:
            row = c.execute("SELECT created_at FROM janus_curiosity_searches WHERE profile_id=? ORDER BY id DESC LIMIT 1", (profile,)).fetchone()
        if not row:
            return 1e12
        return max(0.0, time.time() - datetime.fromisoformat(str(row[0]).replace("Z", "+00:00")).timestamp())
    except Exception:
        return 1e12


def _consult_count_today(profile: str) -> int:
    try:
        with _db() as c:
            row = c.execute("SELECT COUNT(*) FROM janus_core_consults WHERE profile_id=? AND substr(created_at,1,10)=? AND status IN ('pending','complete')", (profile, _day())).fetchone()
        return int(row[0] or 0)
    except Exception:
        return 0


def _seconds_since_last_consult(profile: str) -> float:
    try:
        with _db() as c:
            row = c.execute("SELECT created_at FROM janus_core_consults WHERE profile_id=? ORDER BY id DESC LIMIT 1", (profile,)).fetchone()
        if not row:
            return 1e12
        return max(0.0, time.time() - datetime.fromisoformat(str(row[0]).replace("Z", "+00:00")).timestamp())
    except Exception:
        return 1e12


def _topic_terms(texts: list[str]) -> list[str]:
    stop = {"the","and","that","this","with","from","have","what","when","where","which","would","could","should","about","into","your","you","are","was","were","been","will","just","then","than","them","they","their","there","some","more","think","thinking"}
    counts: dict[str, int] = {}
    for text in texts:
        for w in re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", text.lower()):
            if w not in stop:
                counts[w] = counts.get(w, 0) + 1
    return [w for w, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:12]]


def _choose_search(profile: str) -> tuple[str, str, str, str] | None:
    if not ENABLED or not os.environ.get("OPENAI_API_KEY", "").strip() or DAILY_CAP <= 0:
        return None
    counts = _counts_today(profile)
    if counts["total"] >= DAILY_CAP or _seconds_since_last_search(profile) < MIN_GAP_SECONDS:
        return None
    deliberation = _active_deliberation(profile)
    recent = [x["content"] for x in _recent_context(profile, 12)]
    terms = _topic_terms(([deliberation] if deliberation else []) + recent)
    core_index = counts["total"] % len(CORE_NAMES)
    core = CORE_NAMES[core_index]
    if deliberation and counts["relevant"] < RELEVANT_CAP:
        return core, "relevant", f"Find current reliable information that could materially clarify or challenge this question: {deliberation[:1200]}", "Active retained deliberation needs outside evidence."
    if terms and counts["adjacent"] < ADJACENT_CAP:
        return core, "adjacent", "Explore a well-supported topic adjacent to these current interests and find one useful non-obvious connection: " + ", ".join(terms[:6]), "Widen current context by one conceptual step."
    if counts["wander"] < WANDER_CAP:
        seed = hashlib.sha256(f"{profile}:{_day()}:{counts['total']}".encode()).digest()
        topic = _WANDER_TOPICS[int.from_bytes(seed[:4], "big") % len(_WANDER_TOPICS)]
        return core, "wander", f"Learn about {topic}. Prefer something genuinely new and explain why it may be worth remembering.", "Deliberately acquire unrelated raw material for future connections."
    return None


def _perform_search(profile: str, core: str, mode: str, query: str, rationale: str, row_id: int) -> None:
    key = f"search:{profile}:{row_id}"
    try:
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        prompt = (
            f"You are gathering live external evidence for JANUS core '{core}'. Role: {CORE_ROLE[core]} "
            "Search the live web and return a compact evidence note. Distinguish facts from interpretation, mention uncertainty, and prefer high-quality/primary sources. "
            f"Search mode: {mode}. Question: {query}"
        )
        response = client.responses.create(model=MODEL, tools=[{"type": "web_search"}], input=prompt, max_output_tokens=800)
        text = str(getattr(response, "output_text", "") or "").strip()
        sources = _sources(response)
        with _db() as c:
            c.execute("UPDATE janus_curiosity_searches SET result=?,sources_json=?,status='complete',completed_at=? WHERE id=?", (text[:10000], json.dumps(sources, ensure_ascii=False), _now(), row_id))
        _memory(profile, "external_research", f"[{core}/{mode} web search] {query}\n{text}"[:9000])
        _route_core_note(profile, core, text, f"background_{mode}_web")
        # Evidence and Counterpoint always get a copy so retrieved material is not
        # accepted uncritically even when another core initiated the search.
        if core != "evidence":
            janus_sleep_cycle.send("interface", "evidence", f"Audit external research requested by {core}: {text[:3200]}", "external_research_audit")
        if core != "counterpoint":
            janus_sleep_cycle.send("interface", "counterpoint", f"Challenge reliability/relevance of external research requested by {core}: {text[:3200]}", "external_research_audit")
        janus_sleep_cycle.service_work_burst(include_interface=True, only_if_pending=True)
        _event(profile, "curiosity_search_complete", json.dumps({"core": core, "mode": mode, "query": query, "rationale": rationale, "result": text[:2200], "sources": sources[:6]}, ensure_ascii=False))
    except Exception as exc:
        try:
            with _db() as c:
                c.execute("UPDATE janus_curiosity_searches SET status='error',result=?,completed_at=? WHERE id=?", (f"{type(exc).__name__}: {exc}"[:3000], _now(), row_id))
        except Exception:
            pass
        _event(profile, "curiosity_search_error", f"{core}/{mode}: {type(exc).__name__}: {exc}")
    finally:
        with _lock:
            _inflight.discard(key)


def maybe_schedule(profile: str) -> dict[str, Any] | None:
    choice = _choose_search(profile)
    if not choice:
        return None
    core, mode, query, rationale = choice
    stamp = _now()
    with _db() as c:
        cur = c.execute("INSERT INTO janus_curiosity_searches(profile_id,core_name,mode,query,rationale,status,created_at) VALUES(?,?,?,?,?, 'pending', ?)", (profile, core, mode, query[:3000], rationale[:1000], stamp))
        row_id = int(cur.lastrowid)
    key = f"search:{profile}:{row_id}"
    with _lock:
        if key in _inflight:
            return None
        _inflight.add(key)
    _event(profile, "curiosity_search_started", json.dumps({"core": core, "mode": mode, "why": rationale, "query": query}, ensure_ascii=False))
    threading.Thread(target=_perform_search, args=(profile, core, mode, query, rationale, row_id), daemon=True, name=f"janus-web-{core}-{row_id}").start()
    return {"id": row_id, "core": core, "mode": mode, "query": query, "rationale": rationale}


def maybe_consult_background_core(profile: str) -> dict[str, Any] | None:
    if not MODEL_ENABLED or not os.environ.get("OPENAI_API_KEY", "").strip() or CORE_MODEL_DAILY_CAP <= 0:
        return None
    count = _consult_count_today(profile)
    if count >= CORE_MODEL_DAILY_CAP or _seconds_since_last_consult(profile) < CORE_MODEL_MIN_GAP_SECONDS:
        return None
    core = CORE_NAMES[count % len(CORE_NAMES)]
    context = _recent_context(profile, 10)
    active = _active_deliberation(profile)
    if active:
        topic = f"Active retained question: {active}. Recent context: {json.dumps(context[-6:], ensure_ascii=False)}"
    elif context:
        topic = "Choose one useful implication, unresolved question, or connection from this recent retained context: " + json.dumps(context[-6:], ensure_ascii=False)
    else:
        return None
    key = f"consult:{profile}:{core}:{count}"
    with _lock:
        if key in _inflight:
            return None
        _inflight.add(key)

    def run():
        try:
            consult_core(profile, core, topic, use_web=False, mode="background_model")
        finally:
            with _lock:
                _inflight.discard(key)

    threading.Thread(target=run, daemon=True, name=f"janus-consult-{core}").start()
    return {"core": core, "mode": "background_model"}


def status(profile: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "enabled": ENABLED,
        "model_consult_enabled": MODEL_ENABLED,
        "all_cores_capable": list(CORE_NAMES),
        "daily_web_cap": DAILY_CAP,
        "web_min_gap_seconds": MIN_GAP_SECONDS,
        "background_model_daily_cap": CORE_MODEL_DAILY_CAP,
        "background_model_min_gap_seconds": CORE_MODEL_MIN_GAP_SECONDS,
        "model": MODEL,
        "foreground_model": FOREGROUND_MODEL,
    }
    if profile:
        out["today_web"] = _counts_today(profile)
        out["today_model_consults"] = _consult_count_today(profile)
        try:
            with _db() as c:
                rows = c.execute("SELECT core_name,mode,result,completed_at FROM janus_core_consults WHERE profile_id=? AND status='complete' ORDER BY id DESC LIMIT 11", (profile,)).fetchall()
            out["recent_core_consults"] = [dict(r) for r in rows]
        except Exception:
            out["recent_core_consults"] = []
    return out


def _wrap_chat(app) -> None:
    global _chat_wrapper_installed
    if _chat_wrapper_installed:
        return
    route = next((r for r in app.router.routes if getattr(r, "path", None) == "/desktop/chat" and "POST" in (getattr(r, "methods", set()) or set())), None)
    if route is None:
        return
    original_endpoint = route.endpoint
    app.router.routes = [r for r in app.router.routes if r is not route]

    @app.post("/desktop/chat", tags=["desktop"])
    async def substantive_chat(payload: dict[str, Any]):
        profile = str(payload.get("profile_id") or payload.get("username") or "local-user")
        message = str(payload.get("message") or payload.get("text") or "").strip()
        if message:
            try:
                await asyncio.wait_for(asyncio.to_thread(foreground_deliberate, profile, message), timeout=max(8, int(os.environ.get("JANUS_CORE_FOREGROUND_TIMEOUT_SECONDS", "35"))))
            except Exception as exc:
                _event(profile, "core_foreground_error", f"wrapper: {type(exc).__name__}: {exc}")
        result = original_endpoint(payload)
        if inspect.isawaitable(result):
            result = await result
        if isinstance(result, dict):
            result["substantive_core_deliberation"] = True
        return result

    _chat_wrapper_installed = True


def install(app):
    """Install substantive thought, foreground deliberation, and background research."""
    _db().close()
    _install_substantive_thinker()
    _wrap_chat(app)

    import autonomous_hive as hive
    if not getattr(hive, "_curiosity_search_hook_installed", False):
        original = hive.pulse

        def pulse_with_curiosity(profile: str):
            result = original(profile)
            scheduled_web = None
            scheduled_model = None
            try:
                scheduled_web = maybe_schedule(profile)
            except Exception as exc:
                _event(profile, "curiosity_search_error", f"scheduler: {type(exc).__name__}: {exc}")
            try:
                scheduled_model = maybe_consult_background_core(profile)
            except Exception as exc:
                _event(profile, "core_consult_error", f"scheduler: {type(exc).__name__}: {exc}")
            if isinstance(result, dict):
                result["curiosity_search"] = scheduled_web
                result["core_model_consult"] = scheduled_model
            return result

        hive.pulse = pulse_with_curiosity
        hive._curiosity_search_hook_installed = True

    @app.get("/desktop/core-research-status", tags=["desktop"])
    def core_research_status(username: str | None = None):
        return status(username)

    app.state.janus_curiosity_search = True
    app.state.janus_substantive_core_thought = True
    app.state.janus_all_core_research_capability = True
    return app
