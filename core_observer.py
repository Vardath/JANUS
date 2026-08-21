"""Persistent externalizable observation log for the JANUS 11-core runtime.

Records deterministic/core-generated process summaries and message-routing events.
This intentionally does not expose hidden model chain-of-thought.
"""
from __future__ import annotations

from datetime import datetime, timezone
import os, sqlite3
from fastapi import Query

DB_PATH = os.environ.get("JANUS_DB_PATH", "/data/janus.sqlite3")
MAX_ROWS = max(500, int(os.environ.get("JANUS_CORE_OBSERVE_MAX_ROWS", "5000")))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db():
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("""
        CREATE TABLE IF NOT EXISTS janus_core_observe(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL DEFAULT 'global',
            core_name TEXT NOT NULL,
            peer_core TEXT,
            event_type TEXT NOT NULL,
            detail TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_core_observe_core_id ON janus_core_observe(core_name,id DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_core_observe_type_id ON janus_core_observe(event_type,id DESC)")
    return c


def _record(core: str, event_type: str, detail: str, peer: str | None = None, source: str = "global") -> None:
    try:
        with _db() as c:
            c.execute(
                "INSERT INTO janus_core_observe(source,core_name,peer_core,event_type,detail,created_at) VALUES(?,?,?,?,?,?)",
                (source[:32], str(core)[:64], str(peer)[:64] if peer else None, str(event_type)[:64], str(detail)[:4000], _now()),
            )
            count = c.execute("SELECT COUNT(*) FROM janus_core_observe").fetchone()[0]
            if count > MAX_ROWS:
                c.execute("DELETE FROM janus_core_observe WHERE id IN (SELECT id FROM janus_core_observe ORDER BY id ASC LIMIT ?)", (count - MAX_ROWS,))
    except Exception:
        pass


def install(app, cycle):
    if not getattr(cycle, "_observer_installed", False):
        cycle._observer_installed = True
        original_think = cycle._think
        original_send = cycle.send

        def observed_think(core_state, incoming):
            result = original_think(core_state, incoming)
            _record(core_state.name, "process_note", result)
            return result

        def observed_send(sender, recipient, content, kind="peer"):
            original_send(sender, recipient, content, kind)
            if sender in cycle.cores and recipient in cycle.cores and sender != recipient:
                _record(sender, "interaction", content, peer=recipient)

        cycle._think = observed_think
        cycle.send = observed_send

    @app.get("/desktop/core-observe", tags=["desktop"])
    def core_observe(
        username: str | None = Query(default=None),
        core: str = Query(default="all"),
        mode: str = Query(default="all"),
        limit: int = Query(default=200, ge=1, le=500),
    ):
        clauses = []
        args: list[object] = []
        if core and core != "all":
            clauses.append("core_name=?")
            args.append(core)
        if mode == "interactions":
            clauses.append("event_type='interaction'")
        elif mode == "thoughts":
            clauses.append("event_type='process_note'")
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        with _db() as c:
            rows = c.execute(
                f"SELECT id,source,core_name,peer_core,event_type,detail,created_at FROM janus_core_observe{where} ORDER BY id DESC LIMIT ?",
                (*args, limit),
            ).fetchall()
        return {
            "profile": username or "unspecified",
            "core": core,
            "mode": mode,
            "note": "Externalizable process summaries and routed interactions; not hidden model chain-of-thought.",
            "items": [dict(r) for r in rows],
        }

    return cycle
