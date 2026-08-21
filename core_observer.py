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
GLOBAL_PROFILE = "__global__"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db():
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("""
        CREATE TABLE IF NOT EXISTS janus_core_observe(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id TEXT NOT NULL DEFAULT '',
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
    if "profile_id" not in cols:
        c.execute("ALTER TABLE janus_core_observe ADD COLUMN profile_id TEXT NOT NULL DEFAULT ''")
    c.execute("CREATE INDEX IF NOT EXISTS idx_core_observe_profile_id ON janus_core_observe(profile_id,id DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_core_observe_core_id ON janus_core_observe(core_name,id DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_core_observe_type_id ON janus_core_observe(event_type,id DESC)")
    # Old versions may have created an unscoped unique index. Remove it before
    # creating the profile-aware idempotency key.
    c.execute("DROP INDEX IF EXISTS idx_core_observe_source_event")
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_core_observe_profile_source_event ON janus_core_observe(profile_id,source,source_event_id) WHERE source_event_id IS NOT NULL")
    return c


def _trim(c):
    count = c.execute("SELECT COUNT(*) FROM janus_core_observe").fetchone()[0]
    if count > MAX_ROWS:
        c.execute("DELETE FROM janus_core_observe WHERE id IN (SELECT id FROM janus_core_observe ORDER BY id ASC LIMIT ?)", (count - MAX_ROWS,))


def _record(core: str, event_type: str, detail: str, peer: str | None = None, source: str = "global", source_event_id: str | None = None, created_at: str | None = None, profile_id: str = GLOBAL_PROFILE) -> bool:
    try:
        with _db() as c:
            cur=c.execute(
                "INSERT OR IGNORE INTO janus_core_observe(profile_id,source,source_event_id,core_name,peer_core,event_type,detail,created_at) VALUES(?,?,?,?,?,?,?,?)",
                (str(profile_id or GLOBAL_PROFILE)[:128], source[:64], source_event_id[:160] if source_event_id else None, str(core)[:64], str(peer)[:64] if peer else None, str(event_type)[:64], str(detail)[:4000], created_at or _now()),
            )
            _trim(c)
            return bool(cur.rowcount)
    except Exception:
        return False


def ingest_remote_events(device_id: str, events: list[dict], profile_id: str = "") -> int:
    source=("local:"+str(device_id))[:64]
    added=0
    for event in (events or [])[-100:]:
        if not isinstance(event,dict):
            continue
        try:
            event_id=str(event.get("event_id") or event.get("created_at") or "")+":"+str(event.get("core_name") or "")+":"+str(event.get("event_type") or "")
            created=event.get("created_at")
            if isinstance(created,(int,float)):
                created=datetime.fromtimestamp(float(created)/1000.0,timezone.utc).isoformat()
            if _record(
                str(event.get("core_name") or "unknown"),
                str(event.get("event_type") or "process_note"),
                str(event.get("detail") or ""),
                str(event.get("peer_core") or "") or None,
                source=source,
                source_event_id=event_id,
                created_at=str(created or _now()),
                profile_id=profile_id or GLOBAL_PROFILE,
            ):
                added+=1
        except Exception:
            continue
    return added


def record_remote_snapshot(device_id: str, summary: dict, profile_id: str = "") -> int:
    """Persist operational proof even when a client's detailed event batch is empty.

    Each new per-core cycle count becomes one idempotent timestamped snapshot.
    This makes Observe truthful even if a prior app version failed to upload its
    detailed journal, while detailed process/interaction events remain preferred.
    """
    source=("local:"+str(device_id))[:64]
    phase=str(summary.get("phase") or "unknown")[:32]
    cycles=dict(summary.get("cycles") or {})
    now=_now(); added=0
    for core,count in cycles.items():
        try: count=int(count)
        except Exception: continue
        detail=f"Local runtime sync: {core} has completed {count} cycles; society phase={phase}."
        if core=="consensus" and str(summary.get("consensus") or "").strip():
            detail += " Latest consensus: " + str(summary.get("consensus"))[:900]
        elif core=="interface" and str(summary.get("interface") or "").strip():
            detail += " Latest interface state: " + str(summary.get("interface"))[:900]
        if _record(str(core),"runtime_snapshot",detail,source=source,source_event_id=f"snapshot:{core}:{count}",created_at=now,profile_id=profile_id or GLOBAL_PROFILE):
            added+=1
    return added


def install(app, cycle):
    if not getattr(cycle, "_observer_installed", False):
        cycle._observer_installed = True
        original_think = cycle._think
        original_send = cycle.send

        def observed_think(core_state, incoming):
            result = original_think(core_state, incoming)
            _record(core_state.name, "process_note", result, profile_id=GLOBAL_PROFILE)
            return result

        def observed_send(sender, recipient, content, kind="peer"):
            original_send(sender, recipient, content, kind)
            if sender in cycle.cores and recipient in cycle.cores and sender != recipient:
                _record(sender, "interaction", content, peer=recipient, profile_id=GLOBAL_PROFILE)

        cycle._think = observed_think
        cycle.send = observed_send

    app.router.routes=[r for r in app.router.routes if getattr(r,"path",None)!="/desktop/observe"]

    def _query(profile_id="", core="all", mode="all", limit=200):
        clauses=["profile_id IN (?,?)"]; args=[str(profile_id or ""),GLOBAL_PROFILE]
        if core and core!="all": clauses.append("core_name=?"); args.append(core)
        if mode=="interactions": clauses.append("event_type='interaction'")
        elif mode=="thoughts": clauses.append("event_type IN ('process_note','runtime_snapshot','maintenance','phase','self_assessment')")
        where=" WHERE "+" AND ".join(clauses)
        with _db() as c:
            rows=c.execute(f"SELECT id,profile_id,source,core_name,peer_core,event_type,detail,created_at FROM janus_core_observe{where} ORDER BY created_at DESC,id DESC LIMIT ?",(*args,limit)).fetchall()
        return [dict(r) for r in rows]

    def _live_fallback(core="all", mode="all"):
        if mode=="interactions":
            return []
        try:
            runtime=cycle.status(); items=[]
            for name,state in (runtime.get("cores") or {}).items():
                if core not in ("all",name): continue
                detail=str(state.get("last_output") or "").strip()
                if not detail: continue
                items.append({"id":None,"profile_id":GLOBAL_PROFILE,"source":"global-live","core_name":name,"peer_core":None,"event_type":"process_note","detail":detail,"created_at":state.get("last_cycle_at") or _now()})
            # Remote client summaries are also direct operational evidence.
            for device_id,summary in list(getattr(cycle,"_remote_summaries",{}).items())[-8:]:
                received=str(summary.get("received_at") or _now())
                for name,count in dict(summary.get("cycles") or {}).items():
                    if core not in ("all",name): continue
                    items.append({"id":None,"profile_id":"","source":"local-live:"+str(device_id)[:40],"core_name":name,"peer_core":None,"event_type":"runtime_snapshot","detail":f"Synced local runtime: {name} cycle count={count}; phase={summary.get('phase','unknown')}.","created_at":received})
            items.sort(key=lambda x:str(x.get("created_at") or ""),reverse=True)
            return items
        except Exception:
            return []

    @app.get("/desktop/core-observe", tags=["desktop"])
    def core_observe(username: str | None=Query(default=None), core: str=Query(default="all"), mode: str=Query(default="all"), limit: int=Query(default=200,ge=1,le=500)):
        rows=_query(username or "",core,mode,limit)
        if not rows: rows=_live_fallback(core,mode)[:limit]
        return {"profile":username or "unspecified","core":core,"mode":mode,"note":"Externalizable process summaries and routed interactions; not hidden model chain-of-thought.","items":rows}

    @app.get("/desktop/observe", tags=["desktop"])
    def observe_compat(username: str=Query(...), limit: int=Query(default=200,ge=1,le=500)):
        rows=_query(username,"all","all",limit)
        if not rows: rows=_live_fallback("all","all")[:limit]
        notes=[]
        for r in rows:
            src="local" if str(r.get("source") or "").startswith("local") else "global"
            core=str(r.get("core_name") or "core").replace("_"," ")
            peer=str(r.get("peer_core") or "").replace("_"," ")
            title=f"{src} · {core}"
            if r.get("event_type")=="interaction" and peer: title+=f" → {peer}"
            else: title+=f" · {str(r.get('event_type') or 'note').replace('_',' ')}"
            notes.append({"id":r.get("id"),"event_type":title,"detail":r.get("detail"),"created_at":r.get("created_at"),"core_name":r.get("core_name"),"peer_core":r.get("peer_core"),"source":r.get("source")})
        return {"status":"online","profile":username,"notes":notes,"note":"All 11 core process summaries and routed interactions. These are externalizable runtime notes, not hidden model chain-of-thought."}

    return cycle
