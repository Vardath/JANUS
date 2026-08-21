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
            source_event_id TEXT,
            core_name TEXT NOT NULL,
            peer_core TEXT,
            event_type TEXT NOT NULL,
            detail TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    cols={r[1] for r in c.execute("PRAGMA table_info(janus_core_observe)")}
    if "source_event_id" not in cols:
        c.execute("ALTER TABLE janus_core_observe ADD COLUMN source_event_id TEXT")
    c.execute("CREATE INDEX IF NOT EXISTS idx_core_observe_core_id ON janus_core_observe(core_name,id DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_core_observe_type_id ON janus_core_observe(event_type,id DESC)")
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_core_observe_source_event ON janus_core_observe(source,source_event_id) WHERE source_event_id IS NOT NULL")
    return c


def _trim(c):
    count = c.execute("SELECT COUNT(*) FROM janus_core_observe").fetchone()[0]
    if count > MAX_ROWS:
        c.execute("DELETE FROM janus_core_observe WHERE id IN (SELECT id FROM janus_core_observe ORDER BY id ASC LIMIT ?)", (count - MAX_ROWS,))


def _record(core: str, event_type: str, detail: str, peer: str | None = None, source: str = "global", source_event_id: str | None = None, created_at: str | None = None) -> None:
    try:
        with _db() as c:
            c.execute(
                "INSERT OR IGNORE INTO janus_core_observe(source,source_event_id,core_name,peer_core,event_type,detail,created_at) VALUES(?,?,?,?,?,?,?)",
                (source[:32], source_event_id[:128] if source_event_id else None, str(core)[:64], str(peer)[:64] if peer else None, str(event_type)[:64], str(detail)[:4000], created_at or _now()),
            )
            _trim(c)
    except Exception:
        pass


def ingest_remote_events(device_id: str, events: list[dict]) -> int:
    source=("local:"+str(device_id))[:32]
    added=0
    for event in (events or [])[-100:]:
        if not isinstance(event,dict):
            continue
        try:
            event_id=str(event.get("event_id") or event.get("created_at") or "")+":"+str(event.get("core_name") or "")+":"+str(event.get("event_type") or "")
            created=event.get("created_at")
            if isinstance(created,(int,float)):
                created=datetime.fromtimestamp(float(created)/1000.0,timezone.utc).isoformat()
            _record(
                str(event.get("core_name") or "unknown"),
                str(event.get("event_type") or "process_note"),
                str(event.get("detail") or ""),
                str(event.get("peer_core") or "") or None,
                source=source,
                source_event_id=event_id,
                created_at=str(created or _now()),
            )
            added+=1
        except Exception:
            continue
    return added


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

    # Replace the older generic Observe route with the 11-core observation stream.
    app.router.routes=[r for r in app.router.routes if getattr(r,"path",None)!="/desktop/observe"]

    def _query(core="all", mode="all", limit=200):
        clauses=[]; args=[]
        if core and core!="all": clauses.append("core_name=?"); args.append(core)
        if mode=="interactions": clauses.append("event_type='interaction'")
        elif mode=="thoughts": clauses.append("event_type='process_note'")
        where=(" WHERE "+" AND ".join(clauses)) if clauses else ""
        with _db() as c:
            return c.execute(f"SELECT id,source,core_name,peer_core,event_type,detail,created_at FROM janus_core_observe{where} ORDER BY created_at DESC,id DESC LIMIT ?",(*args,limit)).fetchall()

    @app.get("/desktop/core-observe", tags=["desktop"])
    def core_observe(username: str | None=Query(default=None), core: str=Query(default="all"), mode: str=Query(default="all"), limit: int=Query(default=200,ge=1,le=500)):
        return {"profile":username or "unspecified","core":core,"mode":mode,"note":"Externalizable process summaries and routed interactions; not hidden model chain-of-thought.","items":[dict(r) for r in _query(core,mode,limit)]}

    @app.get("/desktop/observe", tags=["desktop"])
    def observe_compat(username: str=Query(...), limit: int=Query(default=200,ge=1,le=500)):
        rows=[dict(r) for r in _query("all","all",limit)]
        notes=[]
        for r in rows:
            src="local" if str(r.get("source") or "").startswith("local:") else "global"
            core=str(r.get("core_name") or "core").replace("_"," ")
            peer=str(r.get("peer_core") or "").replace("_"," ")
            title=f"{src} · {core}"
            if r.get("event_type")=="interaction" and peer:
                title+=f" → {peer}"
            else:
                title+=f" · {str(r.get('event_type') or 'note').replace('_',' ')}"
            notes.append({"id":r.get("id"),"event_type":title,"detail":r.get("detail"),"created_at":r.get("created_at"),"core_name":r.get("core_name"),"peer_core":r.get("peer_core"),"source":r.get("source")})
        return {"status":"online","profile":username,"notes":notes,"note":"All 11 core process summaries and routed interactions. These are externalizable runtime notes, not hidden model chain-of-thought."}

    return cycle
