"""JANUS dashboard extensions: persistent proactive outbox over the global core."""
from __future__ import annotations
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any
from fastapi import HTTPException, Query
from dashboard_api import app

DB_PATH = os.environ.get("JANUS_DB_PATH", "/data/janus.sqlite3")


def _connect():
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("""CREATE TABLE IF NOT EXISTS janus_message_state (
        profile_id TEXT NOT NULL,
        event_id INTEGER NOT NULL,
        state TEXT NOT NULL DEFAULT 'unread',
        PRIMARY KEY(profile_id,event_id)
    )""")
    c.commit()
    return c


def _message_type(event_type: str, detail: str) -> str:
    text = (detail or "").lower()
    if "?" in (detail or "") or event_type == "question":
        return "Question"
    if "memory" in text or "remember" in text:
        return "Memory"
    if event_type == "background_reflection" or "reflection" in text or "noticed" in text:
        return "Observation"
    return "Follow-up"


def _message_rows(profile: str, limit: int = 50, include_dismissed: bool = False):
    c = _connect()
    try:
        rows = c.execute("""
            SELECT e.id,e.event_type,e.detail,e.created_at,COALESCE(s.state,'unread') AS state
            FROM desktop_events e
            LEFT JOIN janus_message_state s ON s.profile_id=e.profile_id AND s.event_id=e.id
            WHERE e.profile_id=? AND e.event_type IN ('background_reflection','message_candidate','proactive_message','question')
            ORDER BY e.id DESC LIMIT ?
        """, (profile, limit * 2 if not include_dismissed else limit)).fetchall()
        items = []
        for row in rows:
            item = dict(row)
            if not include_dismissed and item["state"] == "dismissed":
                continue
            item["message_type"] = _message_type(item["event_type"], item["detail"])
            items.append(item)
            if len(items) >= limit:
                break
        return items
    finally:
        c.close()


def _presence(profile: str, latest: dict[str, Any] | None) -> str:
    if not latest or not latest.get("created_at"):
        return "Dormant"
    try:
        stamp = datetime.fromisoformat(str(latest["created_at"]).replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - stamp.astimezone(timezone.utc)).total_seconds()
        interval = max(1, int(os.environ.get("JANUS_INTERVAL_MINUTES", "15"))) * 60
        return "Active" if age <= interval * 2 else "Dormant"
    except Exception:
        return "Active"


@app.get('/desktop/messages', tags=['desktop'])
def desktop_messages(
    username: str = Query(...),
    limit: int = Query(default=50, ge=1, le=100),
    include_dismissed: bool = Query(default=False),
):
    items = _message_rows(username, limit, include_dismissed)
    return {
        'profile': username,
        'items': items,
        'unread': sum(1 for x in items if x['state'] == 'unread'),
        'message_types': ['Question', 'Observation', 'Memory', 'Follow-up'],
        'purpose': "JANUS's persistent outbox to the user.",
    }


@app.post('/desktop/messages/{event_id}/state', tags=['desktop'])
def desktop_message_state(event_id: int, payload: dict[str, Any]):
    profile = str(payload.get('profile_id') or payload.get('username') or '').strip()
    state = str(payload.get('state') or 'read').strip().lower()
    if not profile:
        raise HTTPException(400, 'profile_id required')
    if state not in {'unread', 'read', 'dismissed'}:
        raise HTTPException(400, 'state must be unread, read or dismissed')
    c = _connect()
    try:
        exists = c.execute('SELECT 1 FROM desktop_events WHERE id=? AND profile_id=?', (event_id, profile)).fetchone()
        if not exists:
            raise HTTPException(404, 'message not found')
        c.execute("""INSERT INTO janus_message_state(profile_id,event_id,state) VALUES(?,?,?)
                     ON CONFLICT(profile_id,event_id) DO UPDATE SET state=excluded.state""",
                  (profile, event_id, state))
        c.commit()
    finally:
        c.close()
    return {'ok': True, 'event_id': event_id, 'state': state}


@app.get('/desktop/home', tags=['desktop'])
def desktop_home(username: str = Query(...)):
    messages = _message_rows(username, 50)
    c = _connect()
    try:
        row = c.execute("SELECT event_type,detail,created_at FROM desktop_events WHERE profile_id=? ORDER BY id DESC LIMIT 1", (username,)).fetchone()
        latest = dict(row) if row else None
    finally:
        c.close()
    return {
        'profile': username,
        'status': _presence(username, latest),
        'architecture': '7 -> 3 -> 1',
        'unread_messages': sum(1 for x in messages if x['state'] == 'unread'),
        'latest_activity': latest,
        'background_interval_minutes': int(os.environ.get('JANUS_INTERVAL_MINUTES', '15')),
    }
