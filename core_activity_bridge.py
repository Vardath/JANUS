"""Bridge authenticated local-core sync into JANUS profile Activity and Memory.

This is deliberately separate from core_observer.py: Observe is the detailed
runtime journal, while desktop_events/desktop_memory are the user's durable
JANUS profile records. Idempotency receipts prevent sync retries from duplicating
records.
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


def _surface_local_interface(c, profile_id: str, text: str, created_at: str) -> bool:
    """Promote a substantive local Interface conclusion into the real Messages outbox.

    Local cores can cycle every minute, so this is deliberately conservative:
    exact duplicates are rejected and local-background messages have a five-minute
    cooldown. The detailed stream remains available in Observe regardless.
    """
    text = str(text or "").strip()
    if not text:
        return False
    recent = c.execute(
        "SELECT detail,created_at FROM desktop_events WHERE profile_id=? AND event_type='proactive_message' ORDER BY id DESC LIMIT 30",
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
        if old_text.casefold() == text.casefold():
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
        if (current_at - newest_local_at).total_seconds() < 300:
            return False
    payload = json.dumps(
        {"message_type": "Observation", "text": text[:1600], "source": "local-background"},
        ensure_ascii=False,
    )
    c.execute(
        "INSERT INTO desktop_events(profile_id,event_type,detail,created_at) VALUES(?,?,?,?)",
        (profile_id, "proactive_message", payload, created_at),
    )
    return True


def ingest_profile_core_activity(profile_id: str, device_id: str, summary: dict) -> dict:
    """Persist detailed local events plus cycle snapshots into profile history."""
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

            # Promote only substantive autonomous work, not idle maintenance ticks,
            # so Memory remains useful instead of becoming a cycle log.
            idle = "processed 0 peer inputs" in (detail + " " + raw_detail).lower()
            if (not idle) and etype == "process_note" and core in {"memory", "novelty", "consensus", "interface"}:
                c.execute(
                    "INSERT INTO desktop_memory(profile_id,role,content,level,created_at) VALUES(?,?,?,?,?)",
                    (profile_id, f"core:{core}", detail, "working", created),
                )
                added_memory += 1

            # The Interface is the user-facing end of the local 7→2→1→1 society.
            # When its conclusion came from autonomous/self-assessment work, give
            # that conclusion a real chance to reach Messages instead of leaving
            # it stranded in Observe. Routine/user-triggered cycles are excluded.
            lower_raw = raw_detail.lower()
            autonomous = "autonomous" in lower_raw or "self-assessment" in lower_raw or "self_assessment" in lower_raw
            if core == "interface" and etype == "process_note" and (not idle) and autonomous:
                message = detail
                if _surface_local_interface(c, profile_id, message, created):
                    added_messages += 1

        # Cycle-count snapshots are an independent operational proof. They make
        # Activity truthful even when a detailed journal batch was unavailable.
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

        # The synchronized integration state is meaningful working memory. Store
        # it once per new consensus/interface cycle so the Memory screen and the
        # next JANUS process can inspect the same persisted continuity evidence.
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