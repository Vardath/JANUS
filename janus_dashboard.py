"""JANUS dashboard extensions: persistent proactive outbox over the global core."""
from __future__ import annotations
import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any
from fastapi import HTTPException, Query
from dashboard_api import app
from runtime_messaging import install as install_runtime_messaging
from auth import router as auth_router
from src.janus_sleep_cycle import janus_sleep_cycle

DB_PATH = os.environ.get("JANUS_DB_PATH", "/data/janus.sqlite3")

# Configure the local seven-core cycle from deployment settings. This runtime never
# calls a cloud model; it only performs local state transitions/message passing.
janus_sleep_cycle.wake_seconds = max(10, int(os.environ.get("JANUS_WAKE_SECONDS", "300")))
janus_sleep_cycle.sleep_seconds = max(10, int(os.environ.get("JANUS_SLEEP_SECONDS", "600")))


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
    if "reflection" in text or "noticed" in text:
        return "Observation"
    return "Follow-up"


def _decode_message(event_type: str, detail: str) -> tuple[str, str, str]:
    raw = str(detail or "")
    if event_type == "proactive_message":
        try:
            payload = json.loads(raw)
            if isinstance(payload, dict):
                message_type = str(payload.get("message_type") or "Follow-up")
                text = str(payload.get("text") or "").strip()
                source = str(payload.get("source") or "janus")
                if text:
                    return message_type, text, source
        except Exception:
            pass
    return _message_type(event_type, raw), raw, "legacy"


def _message_rows(profile: str, limit: int = 50, include_dismissed: bool = False):
    c = _connect()
    try:
        rows = c.execute("""
            SELECT e.id,e.event_type,e.detail,e.created_at,COALESCE(s.state,'unread') AS state
            FROM desktop_events e
            LEFT JOIN janus_message_state s ON s.profile_id=e.profile_id AND s.event_id=e.id
            WHERE e.profile_id=? AND e.event_type IN ('message_candidate','proactive_message','question')
            ORDER BY e.id DESC LIMIT ?
        """, (profile, limit * 2 if not include_dismissed else limit)).fetchall()
        items = []
        for row in rows:
            item = dict(row)
            if not include_dismissed and item["state"] == "dismissed":
                continue
            message_type, text, source = _decode_message(item["event_type"], item["detail"])
            item["message_type"] = message_type
            item["detail"] = text
            item["source"] = source
            items.append(item)
            if len(items) >= limit:
                break
        return items
    finally:
        c.close()


def _presence(profile: str, latest: dict[str, Any] | None) -> str:
    runtime = janus_sleep_cycle.status()
    if runtime.get("phase") == "wake":
        return "Active"
    if not latest or not latest.get("created_at"):
        return "Dormant"
    try:
        stamp = datetime.fromisoformat(str(latest["created_at"]).replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - stamp.astimezone(timezone.utc)).total_seconds()
        interval = max(1, int(os.environ.get("JANUS_INTERVAL_MINUTES", "15"))) * 60
        return "Active" if age <= interval * 2 else "Dormant"
    except Exception:
        return "Dormant"


@app.on_event("startup")
async def _start_local_core_cycle():
    janus_sleep_cycle.start()


@app.on_event("shutdown")
async def _stop_local_core_cycle():
    janus_sleep_cycle.stop()


@app.get('/desktop/runtime-cores', tags=['desktop'])
def desktop_runtime_cores(username: str | None = Query(default=None)):
    status = janus_sleep_cycle.status()
    return {
        'profile': username or 'unspecified',
        'architecture': '7 -> 3 -> 1',
        'runtime': status,
        'paid_background_api_enabled': os.environ.get('JANUS_SELF_EVALUATION', '0') == '1',
        'note': 'Seven local cores communicate during wake windows and consolidate during sleep. The local cycle makes no external model/API calls.',
    }


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
        'runtime_action': True,
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
    runtime = janus_sleep_cycle.status()
    return {
        'profile': username,
        'status': _presence(username, latest),
        'architecture': '7 -> 3 -> 1',
        'unread_messages': sum(1 for x in messages if x['state'] == 'unread'),
        'latest_activity': latest,
        'background_interval_minutes': int(os.environ.get('JANUS_INTERVAL_MINUTES', '15')),
        'core_phase': runtime.get('phase'),
        'core_runtime': runtime,
        'external_api_budget_used_by_core_cycle': 0,
        'messaging_action': True,
    }


app.include_router(auth_router)
install_runtime_messaging(app)
