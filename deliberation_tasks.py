"""Persistent user-directed deliberation for JANUS.

When the user says things such as "mull it over", "keep thinking about it" or
"ponder that", JANUS records a durable deliberation task.  The task is revisited
by the existing zero-API autonomous hive on later cycles and is routed through
the normal specialists -> hemispheres -> Consensus -> Interface topology.

This module deliberately stores externalizable task state and summaries only;
it is not hidden chain-of-thought and makes no phenomenal-consciousness claim.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import os
import re
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any

DB_PATH = os.environ.get("JANUS_DB_PATH", "/data/janus.sqlite3")
DUE_SECONDS = max(60, int(os.environ.get("JANUS_DELIBERATION_INTERVAL_SECONDS", "900")))
MESSAGE_THRESHOLD = float(os.environ.get("JANUS_DELIBERATION_MESSAGE_THRESHOLD", "0.88"))

# Imperative/continuation language only.  Deliberately excludes ordinary
# questions such as "what do you think about it?".
_INTENT_PATTERNS = (
    re.compile(r"\b(?:mull|ponder)\s+(?:it|that|this|this one|that one|.+?)\s*(?:over)?\b", re.I),
    re.compile(r"\b(?:keep|continue)\s+(?:on\s+)?(?:thinking|pondering|mulling)\b", re.I),
    re.compile(r"\bthink\s+(?:it|that|this)\s+over\b", re.I),
    re.compile(r"\bgive\s+(?:it|that|this)\s+(?:some|more)\s+thought\b", re.I),
    re.compile(r"\b(?:work|keep working)\s+on\s+(?:it|that|this)\s+(?:while|when)\b", re.I),
    re.compile(r"^(?:okay[, ]*|alright[, ]*)?(?:please\s+)?think\s+about\s+(?:it|that|this)(?:\s+(?:some\s+more|for\s+a\s+while))?[.! ]*$", re.I),
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db():
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.executescript(
        """
        CREATE TABLE IF NOT EXISTS janus_deliberation_tasks(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id TEXT NOT NULL,
            source_message TEXT NOT NULL,
            topic TEXT NOT NULL,
            context_excerpt TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            pass_count INTEGER NOT NULL DEFAULT 0,
            current_summary TEXT NOT NULL DEFAULT '',
            avenues_json TEXT NOT NULL DEFAULT '[]',
            last_probe_json TEXT NOT NULL DEFAULT '{}',
            last_message_hash TEXT NOT NULL DEFAULT '',
            last_pass_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_janus_deliberation_profile_status
            ON janus_deliberation_tasks(profile_id,status,updated_at);
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


def _is_deliberation_request(message: str) -> bool:
    text = " ".join(str(message or "").split())
    if not text:
        return False
    lower = text.lower()
    if lower.startswith(("what do you think", "what'd you think", "how do you think", "why do you think")):
        return False
    return any(p.search(text) for p in _INTENT_PATTERNS)


def _recent_context(profile: str, limit: int = 8) -> list[sqlite3.Row]:
    try:
        with _db() as c:
            return c.execute(
                "SELECT id,role,content,level,created_at FROM desktop_memory "
                "WHERE profile_id=? AND length(content)>2 ORDER BY id DESC LIMIT ?",
                (profile, limit),
            ).fetchall()
    except Exception:
        return []


def _topic_for_request(profile: str, message: str) -> tuple[str, str]:
    rows = _recent_context(profile, 10)
    # The wrapper runs before the normal chat endpoint stores this command, so
    # the latest user row is the substantive user turn immediately preceding it.
    previous_user = next((str(r["content"]).strip() for r in rows if str(r["role"]) == "user" and str(r["content"]).strip()), "")
    context_rows = list(reversed(rows[:8]))
    context = "\n".join(f"{r['role']}: {str(r['content'])[:900]}" for r in context_rows)[-6000:]

    text = " ".join(str(message or "").split())
    explicit = ""
    # Handle useful explicit forms such as "keep thinking about whether X".
    m = re.search(r"(?:keep|continue)\s+(?:on\s+)?thinking\s+about\s+(.+)$", text, re.I)
    if m:
        explicit = m.group(1).strip(" .!?\"")
    m2 = re.search(r"(?:mull|ponder)\s+(.+?)(?:\s+over)?[.!?]*$", text, re.I)
    if m2:
        candidate = m2.group(1).strip(" .!?\"")
        if candidate.lower() not in {"it", "that", "this", "this one", "that one"}:
            explicit = candidate

    topic = explicit or previous_user or text
    return topic[:5000], context


def _normalise_topic(text: str) -> str:
    return re.sub(r"\W+", " ", str(text or "").lower()).strip()[:1000]


def create_or_continue(profile: str, source_message: str) -> dict[str, Any] | None:
    if not _is_deliberation_request(source_message):
        return None
    topic, context = _topic_for_request(profile, source_message)
    stamp = _now()
    norm = _normalise_topic(topic)
    with _db() as c:
        rows = c.execute(
            "SELECT * FROM janus_deliberation_tasks WHERE profile_id=? AND status='active' ORDER BY id DESC LIMIT 12",
            (profile,),
        ).fetchall()
        existing = next((r for r in rows if _normalise_topic(r["topic"]) == norm), None)
        if existing:
            c.execute(
                "UPDATE janus_deliberation_tasks SET source_message=?,context_excerpt=?,updated_at=? WHERE id=?",
                (source_message[:3000], context, stamp, int(existing["id"])),
            )
            task_id = int(existing["id"])
            event_type = "deliberation_reaffirmed"
        else:
            cur = c.execute(
                "INSERT INTO janus_deliberation_tasks(profile_id,source_message,topic,context_excerpt,status,created_at,updated_at) "
                "VALUES(?,?,?,?, 'active', ?,?)",
                (profile, source_message[:3000], topic, context, stamp, stamp),
            )
            task_id = int(cur.lastrowid)
            event_type = "deliberation_started"
    _event(profile, event_type, f"Retained deliberation task #{task_id}: {topic[:900]}")
    return {"id": task_id, "profile_id": profile, "topic": topic, "status": "active"}


def _due_task(profile: str):
    with _db() as c:
        rows = c.execute(
            "SELECT * FROM janus_deliberation_tasks WHERE profile_id=? AND status='active' ORDER BY COALESCE(last_pass_at,'') ASC,id ASC",
            (profile,),
        ).fetchall()
    now = time.time()
    for row in rows:
        last = row["last_pass_at"]
        if not last:
            return row
        try:
            dt = datetime.fromisoformat(str(last).replace("Z", "+00:00"))
            if now - dt.timestamp() >= DUE_SECONDS:
                return row
        except Exception:
            return row
    return None


def _choose_memory(hive, profile: str, task, rows):
    if not rows:
        return None
    try:
        used = {int(x) for x in json.loads(task["avenues_json"] or "[]") if str(x).isdigit()}
    except Exception:
        used = set()
    topic_features = hive._features(str(task["topic"]))
    scored = []
    for r in rows:
        try:
            rid = int(r["id"])
            rf = hive._features(str(r["content"]))
            union = max(1, len(topic_features["unique"] | rf["unique"]))
            overlap = len(topic_features["unique"] & rf["unique"]) / union
            level_bonus = 0.08 if str(r["level"]) in {"episodic", "core"} else 0.0
            unused_bonus = 0.18 if rid not in used else 0.0
            scored.append((overlap + level_bonus + unused_bonus, rid, r))
        except Exception:
            continue
    if not scored:
        return rows[int(task["pass_count"] or 0) % len(rows)]
    scored.sort(key=lambda x: (-x[0], x[1]))
    return scored[0][2]


def advance_one(profile: str) -> dict[str, Any] | None:
    """Advance one due user-directed deliberation using the zero-API hive."""
    task = _due_task(profile)
    if task is None:
        return None
    import autonomous_hive as hive
    from src.janus_sleep_cycle import janus_sleep_cycle

    rows = hive._memories(profile, 180)
    memory = _choose_memory(hive, profile, task, rows)
    if memory is None:
        return None

    prior = str(task["current_summary"] or "").strip()
    topic_text = str(task["topic"])
    a = {
        "id": -int(task["id"]),
        "role": "deliberation",
        "level": "working",
        "content": topic_text + (f"\nCurrent working synthesis: {prior}" if prior else ""),
    }
    b = memory
    probe = hive._probe(a, b)
    role_tasks = hive._role_tasks(a, b, probe)
    for target, prompt in role_tasks.items():
        janus_sleep_cycle.send("interface", target, f"User-retained deliberation #{task['id']}: {prompt}", "deliberation_inquiry")
    burst = janus_sleep_cycle.service_work_burst(include_interface=True, only_if_pending=True)

    sig = probe["signals"]
    shared = ", ".join(probe["shared_terms"][:6]) or "no strong lexical overlap"
    numeric = "; ".join(probe["numeric_relations"][:3]) or "no simple exact numeric relation"
    mem_clip = hive._clip(memory["content"], 260)
    pass_no = int(task["pass_count"] or 0) + 1
    synthesis = (
        f"Deliberation pass {pass_no} on: {hive._clip(topic_text, 360)} "
        f"Compared against retained thread #{memory['id']} ({memory['level']}/{memory['role']}): {mem_clip} "
        f"Shared terms: {shared}. Deterministic numeric check: {numeric}. "
        f"Signals—novelty {sig['novelty']:.2f}, conflict {sig['conflict']:.2f}, uncertainty {sig['uncertainty']:.2f}, "
        f"salience {sig['salience']:.2f}, confidence {sig['confidence']:.2f}. "
        "Evidence, Logic, Counterpoint, Context, Memory, Safety and Novelty were re-run before hemispheric/Consensus/Interface integration."
    )

    try:
        avenues = [int(x) for x in json.loads(task["avenues_json"] or "[]") if str(x).isdigit()]
    except Exception:
        avenues = []
    rid = int(memory["id"])
    if rid not in avenues:
        avenues.append(rid)
    avenues = avenues[-64:]
    stamp = _now()
    with _db() as c:
        c.execute(
            "UPDATE janus_deliberation_tasks SET pass_count=?,current_summary=?,avenues_json=?,last_probe_json=?,last_pass_at=?,updated_at=? WHERE id=?",
            (pass_no, synthesis[:7000], json.dumps(avenues), json.dumps(probe, separators=(",", ":")), stamp, stamp, int(task["id"])),
        )
    _event(profile, "deliberation_pass", synthesis)

    # Only interrupt the user for a genuinely strong new candidate. Ordinary
    # passes remain visible in Observe and the task keeps incubating.
    candidate_key = hashlib.sha256((str(task["id"]) + "|" + str(rid) + "|" + shared + "|" + numeric).encode()).hexdigest()
    last_hash = str(task["last_message_hash"] or "")
    message = None
    if float(sig["escalation"]) >= MESSAGE_THRESHOLD and candidate_key != last_hash:
        message = (
            f"I kept thinking about “{hive._clip(topic_text, 180)}”. A new avenue stood out when I compared it with a retained thread about “{hive._clip(memory['content'], 180)}”. "
            f"The overlap is {shared}; {numeric}. The useful next check is whether that overlap reflects the same mechanism or only similar language. "
            "I’m keeping it tentative and will continue the deliberation."
        )
        _event(profile, "proactive_message", json.dumps({"message_type": "Follow-up", "source": "deliberation", "text": message}, ensure_ascii=False))
        with _db() as c:
            c.execute("UPDATE janus_deliberation_tasks SET last_message_hash=?,updated_at=? WHERE id=?", (candidate_key, _now(), int(task["id"])))
        janus_sleep_cycle.send("consensus", "interface", message, "deliberation_candidate")
        janus_sleep_cycle.service_work_burst(include_interface=True, only_if_pending=True)

    return {"task_id": int(task["id"]), "pass": pass_no, "memory_id": rid, "probe": probe, "burst": burst, "message": message}


def _install_hive_hook() -> None:
    import autonomous_hive as hive
    if getattr(hive, "_deliberation_hook_installed", False):
        return
    original = hive.pulse

    def pulse_with_deliberation(profile: str):
        deliberation = None
        try:
            deliberation = advance_one(profile)
        except Exception as exc:
            _event(profile, "deliberation_error", f"{type(exc).__name__}: {exc}")
        result = original(profile)
        if isinstance(result, dict):
            result["deliberation"] = deliberation
        return result

    hive.pulse = pulse_with_deliberation
    hive._deliberation_hook_installed = True


def install(app):
    """Wrap the live chat route and hook user-directed work into the hive."""
    _db().close()
    _install_hive_hook()

    routes = [r for r in app.router.routes if getattr(r, "path", None) == "/desktop/chat" and "POST" in getattr(r, "methods", set())]
    if not routes:
        return app
    old_route = routes[-1]
    base_endpoint = old_route.endpoint
    app.router.routes = [r for r in app.router.routes if r is not old_route]

    @app.post("/desktop/chat", tags=["desktop"])
    async def desktop_chat_with_deliberation(payload: dict[str, Any]):
        profile = str(payload.get("profile_id") or payload.get("username") or "local-user").strip()
        message = str(payload.get("message") or payload.get("text") or "").strip()
        task = create_or_continue(profile, message) if message else None

        result = base_endpoint(payload)
        if inspect.isawaitable(result):
            result = await result
        if not isinstance(result, dict):
            return result

        if task:
            commitment = (
                "I’ve retained this as an active deliberation task. I’ll keep revisiting it during later background cycles, "
                "and I’ll only surface a new message if something materially new emerges."
            )
            reply = str(result.get("reply") or "").rstrip()
            if commitment.lower() not in reply.lower():
                result["reply"] = (reply + "\n\n" + commitment).strip()
            result["deliberation_task"] = task
            _event(profile, "deliberation_committed", f"Task #{task['id']} will continue across later zero-API hive cycles.")
        return result

    @app.get("/desktop/deliberations", tags=["desktop"])
    def desktop_deliberations(username: str, limit: int = 20):
        with _db() as c:
            rows = c.execute(
                "SELECT id,topic,status,pass_count,current_summary,last_pass_at,created_at,updated_at FROM janus_deliberation_tasks "
                "WHERE profile_id=? ORDER BY id DESC LIMIT ?",
                (username, max(1, min(100, int(limit)))),
            ).fetchall()
        return {"profile": username, "items": [dict(r) for r in rows]}

    return app
