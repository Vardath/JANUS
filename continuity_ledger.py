"""Persistent project/question continuity ledger for JANUS.

Tracks durable work independently from transient chat/memory: ideas, tasks, promises,
questions and research threads can move through explicit lifecycle states and supersede
older entries instead of remaining as contradictory 'current' memories.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any, Iterable

DB_PATH = os.getenv("JANUS_DB_PATH", "/data/janus.sqlite3")
KINDS = {"project", "question", "task", "promise", "idea", "research"}
STATES = {
    "proposed", "approved", "active", "investigating", "testing", "blocked",
    "provisional", "completed", "resolved", "deferred", "superseded",
    "contradicted", "reopened", "cancelled",
}
OPEN_STATES = {"proposed", "approved", "active", "investigating", "testing", "blocked", "provisional", "reopened"}
TERMINAL_STATES = {"completed", "resolved", "superseded", "contradicted", "cancelled"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db() -> sqlite3.Connection:
    db = sqlite3.connect(DB_PATH, timeout=20)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    ensure_schema(db)
    return db


def ensure_schema(db: sqlite3.Connection | None = None) -> None:
    own = db is None
    db = db or sqlite3.connect(DB_PATH, timeout=20)
    db.executescript("""
    CREATE TABLE IF NOT EXISTS janus_continuity_items(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      profile_id TEXT NOT NULL,
      kind TEXT NOT NULL,
      title TEXT NOT NULL,
      detail TEXT NOT NULL DEFAULT '',
      state TEXT NOT NULL,
      priority INTEGER NOT NULL DEFAULT 50,
      parent_id INTEGER,
      supersedes_id INTEGER,
      source TEXT NOT NULL DEFAULT 'janus',
      tags_json TEXT NOT NULL DEFAULT '[]',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      closed_at TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_continuity_profile_state
      ON janus_continuity_items(profile_id,state,updated_at DESC);
    CREATE TABLE IF NOT EXISTS janus_continuity_events(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      item_id INTEGER NOT NULL,
      profile_id TEXT NOT NULL,
      event_type TEXT NOT NULL,
      old_state TEXT,
      new_state TEXT,
      note TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_continuity_events_item
      ON janus_continuity_events(item_id,created_at DESC);
    """)
    db.commit()
    if own:
        db.close()


def _validate(kind: str, state: str) -> None:
    if kind not in KINDS:
        raise ValueError(f"unsupported continuity kind: {kind}")
    if state not in STATES:
        raise ValueError(f"unsupported continuity state: {state}")


def _norm(text: str) -> str:
    return re.sub(r"\W+", " ", str(text or "").lower()).strip()[:1200]


def create_item(profile_id: str, kind: str, title: str, detail: str = "", *,
                state: str = "proposed", priority: int = 50, parent_id: int | None = None,
                supersedes_id: int | None = None, source: str = "janus",
                tags: Iterable[str] = ()) -> dict[str, Any]:
    _validate(kind, state)
    title = " ".join((title or "").split()).strip()
    if not profile_id or not title:
        raise ValueError("profile_id and title are required")
    priority = max(0, min(100, int(priority)))
    now = _now()
    with _db() as db:
        cur = db.execute("""INSERT INTO janus_continuity_items
          (profile_id,kind,title,detail,state,priority,parent_id,supersedes_id,source,tags_json,created_at,updated_at,closed_at)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          (profile_id, kind, title, detail or "", state, priority, parent_id, supersedes_id,
           source, json.dumps(sorted(set(tags))), now, now, now if state in TERMINAL_STATES else None))
        item_id = int(cur.lastrowid)
        db.execute("INSERT INTO janus_continuity_events(item_id,profile_id,event_type,new_state,note,created_at) VALUES(?,?,?,?,?,?)",
                   (item_id, profile_id, "created", state, detail[:1000], now))
        if supersedes_id:
            old = db.execute("SELECT state FROM janus_continuity_items WHERE id=? AND profile_id=?", (supersedes_id, profile_id)).fetchone()
            if old:
                db.execute("UPDATE janus_continuity_items SET state='superseded',updated_at=?,closed_at=? WHERE id=? AND profile_id=?",
                           (now, now, supersedes_id, profile_id))
                db.execute("INSERT INTO janus_continuity_events(item_id,profile_id,event_type,old_state,new_state,note,created_at) VALUES(?,?,?,?,?,?,?)",
                           (supersedes_id, profile_id, "superseded", old["state"], "superseded", f"Superseded by item {item_id}", now))
        db.commit()
    return get_item(profile_id, item_id)


def get_item(profile_id: str, item_id: int) -> dict[str, Any]:
    with _db() as db:
        row = db.execute("SELECT * FROM janus_continuity_items WHERE id=? AND profile_id=?", (item_id, profile_id)).fetchone()
    if not row:
        raise KeyError(item_id)
    out = dict(row)
    out["tags"] = json.loads(out.pop("tags_json") or "[]")
    return out


def transition(profile_id: str, item_id: int, new_state: str, note: str = "") -> dict[str, Any]:
    if new_state not in STATES:
        raise ValueError(f"unsupported continuity state: {new_state}")
    now = _now()
    with _db() as db:
        row = db.execute("SELECT state FROM janus_continuity_items WHERE id=? AND profile_id=?", (item_id, profile_id)).fetchone()
        if not row:
            raise KeyError(item_id)
        old = row["state"]
        closed = now if new_state in TERMINAL_STATES else None
        db.execute("UPDATE janus_continuity_items SET state=?,updated_at=?,closed_at=? WHERE id=? AND profile_id=?",
                   (new_state, now, closed, item_id, profile_id))
        db.execute("INSERT INTO janus_continuity_events(item_id,profile_id,event_type,old_state,new_state,note,created_at) VALUES(?,?,?,?,?,?,?)",
                   (item_id, profile_id, "transition", old, new_state, note[:2000], now))
        db.commit()
    return get_item(profile_id, item_id)


def revise(profile_id: str, item_id: int, *, title: str | None = None, detail: str | None = None,
           priority: int | None = None, note: str = "") -> dict[str, Any]:
    current = get_item(profile_id, item_id)
    new_title = current["title"] if title is None else " ".join(title.split()).strip()
    new_detail = current["detail"] if detail is None else detail
    new_priority = current["priority"] if priority is None else max(0, min(100, int(priority)))
    now = _now()
    with _db() as db:
        db.execute("UPDATE janus_continuity_items SET title=?,detail=?,priority=?,updated_at=? WHERE id=? AND profile_id=?",
                   (new_title, new_detail, new_priority, now, item_id, profile_id))
        db.execute("INSERT INTO janus_continuity_events(item_id,profile_id,event_type,old_state,new_state,note,created_at) VALUES(?,?,?,?,?,?,?)",
                   (item_id, profile_id, "revised", current["state"], current["state"], note[:2000], now))
        db.commit()
    return get_item(profile_id, item_id)


def list_items(profile_id: str, *, open_only: bool = False, kind: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    clauses, args = ["profile_id=?"], [profile_id]
    if open_only:
        marks = ",".join("?" for _ in OPEN_STATES)
        clauses.append(f"state IN ({marks})")
        args.extend(sorted(OPEN_STATES))
    if kind:
        if kind not in KINDS:
            raise ValueError(f"unsupported continuity kind: {kind}")
        clauses.append("kind=?")
        args.append(kind)
    args.append(max(1, min(500, int(limit))))
    with _db() as db:
        rows = db.execute(f"SELECT * FROM janus_continuity_items WHERE {' AND '.join(clauses)} ORDER BY priority DESC, updated_at DESC LIMIT ?", args).fetchall()
    result=[]
    for row in rows:
        d=dict(row); d["tags"]=json.loads(d.pop("tags_json") or "[]"); result.append(d)
    return result


def upsert_open(profile_id: str, kind: str, title: str, detail: str = "", *, state: str = "active",
                priority: int = 50, source: str = "janus", tags: Iterable[str] = ()) -> dict[str, Any]:
    """Create or reaffirm an equivalent open item without duplicating it."""
    _validate(kind, state)
    norm = _norm(title)
    for item in list_items(profile_id, open_only=True, kind=kind, limit=200):
        if _norm(item["title"]) == norm:
            if detail and detail != item["detail"]:
                item = revise(profile_id, item["id"], detail=detail, priority=max(priority, item["priority"]), note="Reaffirmed/updated from active continuity source")
            if item["state"] != state and item["state"] in {"proposed", "approved", "reopened"}:
                item = transition(profile_id, item["id"], state, "Advanced by active continuity source")
            return item
    return create_item(profile_id, kind, title, detail, state=state, priority=priority, source=source, tags=tags)


def events(profile_id: str, item_id: int, limit: int = 100) -> list[dict[str, Any]]:
    with _db() as db:
        rows=db.execute("SELECT * FROM janus_continuity_events WHERE profile_id=? AND item_id=? ORDER BY id DESC LIMIT ?",
                        (profile_id,item_id,max(1,min(500,int(limit))))).fetchall()
    return [dict(r) for r in rows]


def continuity_context(profile_id: str, limit: int = 20) -> str:
    """Compact grounding block suitable for Memory/Context/background cognition."""
    items = list_items(profile_id, open_only=True, limit=limit)
    if not items:
        return "No open project/question continuity items."
    lines = ["Open JANUS continuity ledger (explicit durable commitments/questions):"]
    for x in items:
        lines.append(f"- [#{x['id']} {x['kind']}:{x['state']}] {x['title']}" + (f" — {x['detail'][:240]}" if x['detail'] else ""))
    return "\n".join(lines)
