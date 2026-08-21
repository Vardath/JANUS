"""Bridge authenticated local-core sync into JANUS profile Activity and Memory.

Observe remains the detailed runtime journal. Messages are intentionally much
more selective: routine self-assessment, Fano telemetry, maintenance and generic
integration summaries stay in Observe instead of becoming user-facing outbox
items.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
import sqlite3

DB_PATH = os.environ.get("JANUS_DB_PATH", "/data/janus.sqlite3")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db():
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("CREATE TABLE IF NOT EXISTS desktop_memory (id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, level TEXT NOT NULL DEFAULT 'trace', created_at TEXT NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS desktop_events (id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id TEXT NOT NULL, event_type TEXT NOT NULL, detail TEXT NOT NULL, created_at TEXT NOT NULL)")
    c.execute("""CREATE TABLE IF NOT EXISTS janus_core_profile_ingest(
        profile_id TEXT NOT NULL,
        source_event_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY(profile_id, source_event_id)
    )""")
    return c


def _claim(c, profile_id: str, key: str, created_at: str) -> bool:
    cur = c.execute(
        "INSERT OR IGNORE INTO janus_core_profile_ingest(profile_id,source_event_id,created_at) VALUES(?,?,?)",
        (profile_id[:128], key[:220], created_at),
    )
    return bool(cur.rowcount)


def _low_value_message(text: str) -> bool:
    t = str(text or "").casefold()
    markers = (
        "self-assessment", "self_assessment", "active fano direction", "fano d",
        "processed 0 peer inputs", "processed 1 peer inputs",
        "interface updated the user-facing shared state",
        "interface formulated the shared state around",
        "integration: combine hemispheres", "autonomous boundary task",
        "maintenance pass",
    )
    return (not t.strip()) or any(m in t for m in markers)


def _message_worthy(text: str) -> bool:
    if _low_value_message(text):
        return False
    t = str(text or "").casefold()
    useful = (
        "?", "conclusion", "found ", "discovered", "new connection",
        "new finding", "unresolved question", "needs your input",
        "recommend", "warning", "important",
    )
    return any(m in t for m in useful)


def _canonical(text: str) -> str:
    import re
    t = str(text or "").casefold()
    t = re.sub(r"\d+(?:\.\d+)?", "#", t)
    t = re.sub(r"[^a-z?#]+", " ", t)
    return " ".join(t.split())


def _surface_local_interface(c, profile_id: str, text: str, created_at: str) -> bool:
    text = str(text or "").strip()
    if not _message_worthy(text):
        return False
    sig = _canonical(text)
    recent = c.execute(
        "SELECT detail,created_at FROM desktop_events WHERE profile_id=? AND event_type='proactive_message' ORDER BY id DESC LIMIT 40",
        (profile_id,),
    ).fetchall()
    newest_local_at = None
    for row in recent:
        raw = str(row["detail"] or "")
        try:
            item = json.loads(raw)
        except Exception:
            item = {}
        old_text = str(item.get("text") or raw).strip()
        if _canonical(old_text) == sig:
            return False
        if item.get("source") == "local-background" and newest_local_at is None:
            try:
                newest_local_at = datetime.fromisoformat(str(row["created_at"]).replace("Z", "+00:00"))
            except Exception:
                newest_local_at = None
    try:
        current_at = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
    except Exception:
        current_at = datetime.now(timezone.utc)
    if newest_local_at is not None:
        if newest_local_at.tzinfo is None:
            newest_local_at = newest_local_at.replace(tzinfo=timezone.utc)
        if current_at.tzinfo is None:
            current_at = current_at.replace(tzinfo=timezone.utc)
        if (current_at - newest_local_at).total_seconds() < 600:
            return False
    message_type = "Question" if "?" in text else "Observation"
    payload = json.dumps(
        {"message_type": message_type, "text": text[:1600], "source": "local-background"},
        ensure_ascii=False,
    )
    c.execute(
        "INSERT INTO desktop_events(profile_id,event_type,detail,created_at) VALUES(?,?,?,?)",
        (profile_id, "proactive_message", payload, created_at),
    )
    return True


def ingest_profile_core_activity(profile_id: str, device_id: str, summary: dict) -> dict:
    profile_id = str(profile_id or "").strip()[:128]
    if not profile_id:
        return {"activity": 0, "memory": 0, "snapshots": 0, "messages": 0}
    device = str(device_id or "device")[:96]
    events = list(summary.get("observe_events") or [])[-100:]
    added_activity = added_memory = snapshots = added_messages = 0

    with _db() as c:
        for e in events:
            if not isinstance(e, dict):
                continue
            core = str(e.get("core_name") or "unknown")[:64]
            peer = str(e.get("peer_core") or "")[:64]
            etype = str(e.get("event_type") or "process_note")[:64]
            detail = str(e.get("detail") or "").strip()[:5000]
            raw_detail = str(e.get("raw_detail") or "").strip()[:5000]
            if not detail:
                continue
            raw_created = e.get("created_at")
            if isinstance(raw_created, (int, float)):
                created = datetime.fromtimestamp(float(raw_created) / 1000.0, timezone.utc).isoformat()
            else:
                created = str(raw_created or _now())
            eid = str(e.get("event_id") or f"{created}:{core}:{etype}:{peer}")
            key = f"event:{device}:{eid}"
            if not _claim(c, profile_id, key, created):
                continue
            route = f" -> {peer}" if peer else ""
            readable = f"[{core}{route}] {detail}"
            c.execute(
                "INSERT INTO desktop_events(profile_id,event_type,detail,created_at) VALUES(?,?,?,?)",
                (profile_id, f"core_{etype}"[:64], readable, created),
            )
            added_activity += 1

            idle = "processed 0 peer inputs" in (detail + " " + raw_detail).lower()
            if (not idle) and etype == "process_note" and core in {"memory", "novelty", "consensus", "interface"}:
                c.execute(
                    "INSERT INTO desktop_memory(profile_id,role,content,level,created_at) VALUES(?,?,?,?,?)",
                    (profile_id, f"core:{core}", detail, "working", created),
                )
                added_memory += 1

            # Only genuinely user-relevant autonomous Interface outcomes become
            # Messages. Self-assessment and telemetry remain visible in Observe.
            lower_raw = raw_detail.lower()
            autonomous = "autonomous" in lower_raw
            candidate = raw_detail if _message_worthy(raw_detail) else detail
            if core == "interface" and etype == "process_note" and (not idle) and autonomous and _message_worthy(candidate):
                if _surface_local_interface(c, profile_id, candidate, created):
                    added_messages += 1

        phase = str(summary.get("phase") or "unknown")[:32]
        cycles = dict(summary.get("cycles") or {})
        for core, count in cycles.items():
            try:
                count = int(count)
            except Exception:
                continue
            created = _now()
            key = f"snapshot:{device}:{core}:{count}"
            if not _claim(c, profile_id, key, created):
                continue
            detail = f"Local core {core} reached cycle {count}; society phase={phase}; device={device}."
            c.execute(
                "INSERT INTO desktop_events(profile_id,event_type,detail,created_at) VALUES(?,?,?,?)",
                (profile_id, "core_runtime_snapshot", detail, created),
            )
            snapshots += 1

        for core, field in (("consensus", "consensus"), ("interface", "interface")):
            text = str(summary.get(field) or "").strip()[:5000]
            if not text:
                continue
            try:
                count = int(cycles.get(core, 0))
            except Exception:
                count = 0
            created = _now()
            key = f"state-memory:{device}:{core}:{count}"
            if _claim(c, profile_id, key, created):
                c.execute(
                    "INSERT INTO desktop_memory(profile_id,role,content,level,created_at) VALUES(?,?,?,?,?)",
                    (profile_id, f"core:{core}", text, "working", created),
                )
                added_memory += 1
        c.commit()

    return {"activity": added_activity, "memory": added_memory, "snapshots": snapshots, "messages": added_messages}
