"""Always-responsive JANUS interface chat route.

Uses latest 11-core consensus/interface state immediately. Other cores may be
asleep; they continue to update shared state asynchronously. The user turn is
stored before model work so transient model/network failure does not lose it.
Client message IDs make Android offline retries idempotent.
"""
from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import time
from typing import Any

from fastapi import HTTPException
from openai import AsyncOpenAI

from dashboard_api import JANUS_SELF_KNOWLEDGE, _recent_context, _store
from src.janus_sleep_cycle import janus_sleep_cycle

DB_PATH = os.environ.get("JANUS_DB_PATH", "/data/janus.sqlite3")
GLOBAL_PROFILE="__global__"


def _receipt_db():
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute(
        """CREATE TABLE IF NOT EXISTS janus_chat_receipts(
        client_message_id TEXT PRIMARY KEY,
        profile_id TEXT NOT NULL,
        status TEXT NOT NULL,
        response_json TEXT,
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL
        )"""
    )
    return c


def _claim_message(client_message_id: str, profile: str):
    if not client_message_id:
        return None
    now = int(time.time())
    with _receipt_db() as c:
        row = c.execute("SELECT status,response_json,updated_at FROM janus_chat_receipts WHERE client_message_id=?",(client_message_id,)).fetchone()
        if row:
            if row["status"] == "done" and row["response_json"]:
                try:return json.loads(row["response_json"])
                except Exception:pass
            if row["status"] == "processing" and now - int(row["updated_at"] or 0) <= 180:return "processing"
            c.execute("UPDATE janus_chat_receipts SET profile_id=?,status='processing',response_json=NULL,updated_at=? WHERE client_message_id=?",(profile, now, client_message_id))
            return None
        c.execute("INSERT INTO janus_chat_receipts(client_message_id,profile_id,status,response_json,created_at,updated_at) VALUES(?,?,'processing',NULL,?,?)",(client_message_id, profile, now, now))
    return None


def _finish_message(client_message_id: str, profile: str, response: dict[str, Any]):
    if not client_message_id:return
    now = int(time.time())
    with _receipt_db() as c:
        c.execute("""INSERT INTO janus_chat_receipts(client_message_id,profile_id,status,response_json,created_at,updated_at)
            VALUES(?,?,'done',?,?,?) ON CONFLICT(client_message_id) DO UPDATE SET
            profile_id=excluded.profile_id,status='done',response_json=excluded.response_json,updated_at=excluded.updated_at""",
            (client_message_id, profile, json.dumps(response), now, now))


def _live_runtime_evidence(runtime: dict[str, Any], profile: str) -> str:
    """Build a compact factual block the interface model may safely rely on."""
    cores = runtime.get("cores") or {}
    lines = [
        "LIVE JANUS RUNTIME EVIDENCE (server-observed, not a hypothetical architecture):",
        f"architecture={runtime.get('architecture', 'unknown')}",f"topology={runtime.get('topology', 'unknown')}",
        f"core_count={runtime.get('core_count', len(cores) or 'unknown')}",f"society_phase={runtime.get('phase', 'unknown')}",
        f"interface_awake={bool(runtime.get('interface_awake', (cores.get('interface') or {}).get('awake', False)))}",
        f"persistent_storage={bool(runtime.get('persistent_storage', False))}",f"remote_clients={runtime.get('remote_clients', 0)}",
    ]
    for name, state in cores.items():
        lines.append(f"server core {name}: awake={bool(state.get('awake'))}; cycles={state.get('cycle_count', 0)}; pending={state.get('pending_messages', 0)}; last_cycle={state.get('last_cycle_at') or 'never'}; last_output={str(state.get('last_output') or '')[:220]}")
    try:
        with sqlite3.connect(DB_PATH, timeout=5) as c:
            c.row_factory = sqlite3.Row
            try:
                row = c.execute("SELECT created_at,disagreement_score,action_summary FROM janus_self_assessment ORDER BY id DESC LIMIT 1").fetchone()
                if row:lines.append(f"latest_self_assessment: at={row['created_at']}; disagreement={float(row['disagreement_score']):.3f}; summary={str(row['action_summary'])[:500]}")
            except sqlite3.Error:pass
            try:
                cols={r[1] for r in c.execute("PRAGMA table_info(janus_core_observe)")}
                if "profile_id" in cols:
                    rows = c.execute("SELECT source,core_name,peer_core,event_type,detail,created_at FROM janus_core_observe WHERE profile_id IN (?,?) ORDER BY id DESC LIMIT 24",(profile,GLOBAL_PROFILE)).fetchall()
                else:
                    rows = c.execute("SELECT source,core_name,peer_core,event_type,detail,created_at FROM janus_core_observe ORDER BY id DESC LIMIT 24").fetchall()
                if rows:
                    lines.append("recent_observable_core_activity (same journal exposed by Observe):")
                    for row in rows:
                        peer = f" -> {row['peer_core']}" if row['peer_core'] else ""
                        lines.append(f"- {row['created_at']} {row['source']} {row['core_name']}{peer} [{row['event_type']}]: {str(row['detail'])[:260]}")
                else:lines.append("recent_observable_core_activity: no persisted observation rows currently visible for this profile")
            except sqlite3.Error:pass
    except Exception:pass
    # The global runtime also retains latest compact client summaries. These are
    # operational telemetry and may verify client cycling even before detailed
    # observation rows arrive.
    try:
        remote=list(getattr(janus_sleep_cycle,"_remote_summaries",{}).items())[-4:]
        if remote:
            lines.append("recent_client_runtime_syncs:")
            for device,summary in remote:
                lines.append(f"- device={str(device)[:80]}; received={summary.get('received_at')}; phase={summary.get('phase')}; cycles={summary.get('cycles')}; consensus={str(summary.get('consensus') or '')[:220]}")
    except Exception:pass
    return "\n".join(lines)


def install(app):
    app.router.routes = [r for r in app.router.routes if getattr(r, "path", None) != "/desktop/chat"]

    @app.post("/desktop/chat", tags=["desktop"])
    async def desktop_chat_interface(payload: dict[str, Any]):
        profile = str(payload.get("profile_id") or payload.get("username") or "local-user")
        message = str(payload.get("message") or payload.get("text") or "").strip()
        client_message_id = str(payload.get("client_message_id") or "").strip()[:128]
        if not message:raise HTTPException(400, "message required")
        claimed = _claim_message(client_message_id, profile)
        if isinstance(claimed, dict):claimed["deduplicated"] = True; return claimed
        if claimed == "processing":raise HTTPException(409, "This message is already being processed; retry shortly")
        _store(profile, "user", message, "chat_input")
        try:
            service = getattr(janus_sleep_cycle, "service_interface_once", None)
            if service:service()
        except Exception:pass
        runtime = janus_sleep_cycle.status()
        latest_consensus = str(runtime.get("last_consensus") or "").strip(); latest_interface = str(runtime.get("last_interface") or "").strip()
        history = _recent_context(profile); evidence = _live_runtime_evidence(runtime,profile)
        if not os.environ.get("OPENAI_API_KEY"):
            reply = "I received and stored your message. My external response model is temporarily unavailable, but my interface core is still active and the 11-core runtime state remains persisted. I will retain this turn for follow-up when model access returns."
            _store(profile, "assistant", reply, "chat_fallback", "working")
            result = {"reply": reply, "profile": profile, "mode": "interface_fallback", "stored": True,"client_message_id": client_message_id}; _finish_message(client_message_id, profile, result); return result
        model = os.environ.get("JANUS_MODEL", "gpt-5.6")
        instructions = JANUS_SELF_KNOWLEDGE + """

CURRENT RUNTIME POLICY:
JANUS has 11 functional cores arranged 7 specialists -> 2 hemispheres -> consensus -> interface.
The interface core is always available to the user while the other ten cores may sleep or wake independently.
You are given a LIVE JANUS RUNTIME EVIDENCE block produced by this running server. Treat it as direct runtime telemetry.
The recent_observable_core_activity section is the same profile-scoped persistent journal exposed in the Observe UI. recent_client_runtime_syncs is direct synchronized device telemetry.
When these sections show timestamped activity, cycle-count changes, interactions or runtime snapshots, you may accurately say background processing occurred. When they do not, say that evidence is absent rather than assuming activity.
Do not claim all cores are awake when telemetry says otherwise, and do not invent unobserved private reasoning. Externalizable process notes are summaries of computation, not hidden chain-of-thought.
Answer as the main interface core using the latest synchronized consensus, runtime evidence, and conversation history.
"""
        state_block = evidence + f"\nLatest consensus state: {latest_consensus or '[no recent consensus summary]'}" + f"\nLatest interface state: {latest_interface or '[no recent interface summary]'}" + f"\nInterface policy: {runtime.get('interface_policy', 'always_available')}"
        inp = state_block + (f"\n\nRecent conversation:\n{history}" if history else "") + f"\n\nCurrent user message:\n{message}"
        timeout_seconds = max(30, int(os.environ.get("JANUS_CHAT_TIMEOUT_SECONDS", "105")))
        try:
            async def call_model():
                response = await AsyncOpenAI().responses.create(model=model, instructions=instructions, input=inp)
                return (response.output_text or "").strip()
            reply = await asyncio.wait_for(call_model(), timeout=timeout_seconds)
            if not reply:raise RuntimeError("empty response")
        except Exception as exc:
            _store(profile, "system", f"chat_model_deferred: {type(exc).__name__}: {exc}", "chat_error")
            reply = "I received and stored that. My interface is still here, but the external response model did not complete this turn in time. My persisted 11-core runtime may continue processing it, and I will preserve the thread for the next response rather than losing your message."
            _store(profile, "assistant", reply, "chat_fallback", "working")
            result = {"reply": reply,"profile": profile,"model": model,"mode": "interface_timeout_fallback","stored": True,"society_phase": runtime.get("phase"),"client_message_id": client_message_id}; _finish_message(client_message_id, profile, result); return result
        _store(profile, "assistant", reply, "chat_output"); _store(profile, "process", "Interface answered from live 11-core runtime evidence plus latest synchronized consensus.", "synthesis_note")
        result = {"reply": reply,"profile": profile,"model": model,"mode": "interface_live","society_phase": runtime.get("phase"),"interface_always_available": True,"runtime_evidence": True,"client_message_id": client_message_id}; _finish_message(client_message_id, profile, result); return result
