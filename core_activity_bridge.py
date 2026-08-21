"""Bridge authenticated local-core sync into JANUS profile Activity and Memory.

This is deliberately separate from core_observer.py: Observe is the detailed
runtime journal, while desktop_events/desktop_memory are the user's durable
JANUS profile records. Idempotency receipts prevent sync retries from duplicating
records.
"""
from __future__ import annotations

from datetime import datetime, timezone
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


def ingest_profile_core_activity(profile_id: str, device_id: str, summary: dict) -> dict:
    """Persist detailed local events plus cycle snapshots into profile history."""
    profile_id = str(profile_id or "").strip()[:128]
    if not profile_id:
        return {"activity": 0, "memory": 0, "snapshots": 0}
    device = str(device_id or "device")[:96]
    events = list(summary.get("observe_events") or [])[-100:]
    added_activity = added_memory = snapshots = 0

    with _db() as c:
        for e in events:
            if not isinstance(e, dict):
                continue
            core = str(e.get("core_name") or "unknown")[:64]
            peer = str(e.get("peer_core") or "")[:64]
            etype = str(e.get("event_type") or "process_note")[:64]
            detail = str(e.get("detail") or "").strip()[:5000]
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
            idle = "processed 0 peer inputs" in detail.lower()
            if (not idle) and etype == "process_note" and core in {"memory", "novelty", "consensus", "interface"}:
                c.execute(
                    "INSERT INTO desktop_memory(profile_id,role,content,level,created_at) VALUES(?,?,?,?,?)",
                    (profile_id, f"core:{core}", detail, "working", created),
                )
                added_memory += 1

        # Cycle-count snapshots are an independent operational proof. They make
        # Activity truthful even when a detailed journal batch was unavailable.
        phase = str(summary.get("phase") or "unknown")[:32]
        for core, count in dict(summary.get("cycles") or {}).items():
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
        c.commit()

    return {"activity": added_activity, "memory": added_memory, "snapshots": snapshots}
