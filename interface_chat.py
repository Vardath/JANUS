"""Always-responsive JANUS interface chat route.

The interface answers ordinary chat from the latest 11-core state. Questions
about persistence/background work are verified deterministically from the same
device journal exposed by Android Observe whenever that telemetry is supplied.
"""
from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from openai import AsyncOpenAI

from dashboard_api import JANUS_SELF_KNOWLEDGE, _recent_context, _store
from src.janus_sleep_cycle import janus_sleep_cycle

DB_PATH = os.environ.get("JANUS_DB_PATH", "/data/janus.sqlite3")
GLOBAL_PROFILE = "__global__"


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
        row = c.execute(
            "SELECT status,response_json,updated_at FROM janus_chat_receipts WHERE client_message_id=?",
            (client_message_id,),
        ).fetchone()
        if row:
            if row["status"] == "done" and row["response_json"]:
                try:
                    return json.loads(row["response_json"])
                except Exception:
                    pass
            if row["status"] == "processing" and now - int(row["updated_at"] or 0) <= 180:
                return "processing"
            c.execute(
                "UPDATE janus_chat_receipts SET profile_id=?,status='processing',response_json=NULL,updated_at=? WHERE client_message_id=?",
                (profile, now, client_message_id),
            )
            return None
        c.execute(
            "INSERT INTO janus_chat_receipts(client_message_id,profile_id,status,response_json,created_at,updated_at) VALUES(?,?,'processing',NULL,?,?)",
            (client_message_id, profile, now, now),
        )
    return None


def _finish_message(client_message_id: str, profile: str, response: dict[str, Any]):
    if not client_message_id:
        return
    now = int(time.time())
    with _receipt_db() as c:
        c.execute(
            """INSERT INTO janus_chat_receipts(client_message_id,profile_id,status,response_json,created_at,updated_at)
            VALUES(?,?,'done',?,?,?) ON CONFLICT(client_message_id) DO UPDATE SET
            profile_id=excluded.profile_id,status='done',response_json=excluded.response_json,updated_at=excluded.updated_at""",
            (client_message_id, profile, json.dumps(response), now, now),
        )


def _parse_device_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    raw = payload.get("local_runtime_evidence")
    if not raw:
        return {}
    if isinstance(raw, dict):
        data = raw
    else:
        try:
            data = json.loads(str(raw))
        except Exception:
            return {}
    if not isinstance(data, dict):
        return {}
    # Bound everything accepted from the app before putting it into prompts/logs.
    events = data.get("recent_events") if isinstance(data.get("recent_events"), list) else []
    clean_events = []
    for x in events[-48:]:
        if not isinstance(x, dict):
            continue
        clean_events.append({
            "at": int(x.get("at") or 0),
            "core": str(x.get("core") or "core")[:64],
            "peer": str(x.get("peer") or "")[:64],
            "type": str(x.get("type") or "event")[:64],
            "summary": str(x.get("summary") or "")[:700],
        })
    cycles = data.get("cycles") if isinstance(data.get("cycles"), dict) else {}
    clean_cycles = {str(k)[:64]: int(v or 0) for k, v in list(cycles.items())[:16]}
    return {
        "device_id": str(data.get("device_id") or "")[:96],
        "phase": str(data.get("phase") or "")[:32],
        "sync_state": str(data.get("sync_state") or "")[:32],
        "last_sync_at": int(data.get("last_sync_at") or 0),
        "last_disagreement_score": int(data.get("last_disagreement_score") or 0),
        "cycles": clean_cycles,
        "recent_events": clean_events,
        "consensus": str(data.get("consensus") or "")[:900],
        "interface": str(data.get("interface") or "")[:900],
    }


def _fmt_ms(ms: int) -> str:
    if not ms:
        return "unknown time"
    try:
        return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return str(ms)


def _verification_intent(message: str) -> bool:
    m = message.lower()
    keys = (
        "while i was away", "while i've been away", "while i have been away",
        "what have you been doing", "what did you do", "background",
        "verify", "verification", "persistence", "persist", "autonomous",
        "between messages", "while i was gone", "while i've been gone",
    )
    return any(k in m for k in keys)


def _meaningful_events(device: dict[str, Any]) -> list[dict[str, Any]]:
    events = device.get("recent_events") or []
    preferred = {
        "autonomous_pulse", "self_assessment", "process_note", "interaction",
        "phase", "maintenance", "user_topic",
    }
    return [x for x in events if x.get("type") in preferred and x.get("at")]


def _deterministic_device_verification(device: dict[str, Any]) -> str | None:
    events = _meaningful_events(device)
    if not events:
        return None
    latest = events[-1]
    earliest = events[0]
    cycles = device.get("cycles") or {}
    active_cycles = {k: v for k, v in cycles.items() if int(v or 0) > 0}
    total = sum(int(v or 0) for v in active_cycles.values())

    autonomous = [x for x in events if x.get("type") == "autonomous_pulse"]
    assessments = [x for x in events if x.get("type") == "self_assessment"]
    interactions = [x for x in events if x.get("type") == "interaction"]
    notes = [x for x in events if x.get("type") == "process_note"]

    lines = [
        "Yes. The local device journal verifies that background processing occurred.",
        "",
        f"The current evidence window runs from {_fmt_ms(int(earliest.get('at') or 0))} to {_fmt_ms(int(latest.get('at') or 0))}.",
    ]
    if active_cycles:
        top = sorted(active_cycles.items(), key=lambda kv: kv[1], reverse=True)[:6]
        lines.append(
            "The phone reports local core cycle counts including "
            + ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in top)
            + f"; {total} cycles are represented across the reported counters."
        )
    if autonomous:
        x = autonomous[-1]
        lines.append(f"An autonomous memory/revisit pulse was recorded at {_fmt_ms(int(x['at']))}: {x.get('summary','')[:360]}")
    if assessments:
        x = assessments[-1]
        lines.append(f"A self-assessment was recorded at {_fmt_ms(int(x['at']))}: {x.get('summary','')[:360]}")
    if interactions:
        x = interactions[-1]
        peer = f" → {x.get('peer')}" if x.get("peer") else ""
        lines.append(
            f"A recent routed interaction at {_fmt_ms(int(x['at']))} was {x.get('core','core')}{peer}: "
            f"{x.get('summary','')[:360]}"
        )
    elif notes:
        x = notes[-1]
        lines.append(f"A recent process note at {_fmt_ms(int(x['at']))} from {x.get('core','core')}: {x.get('summary','')[:360]}")
    if device.get("last_disagreement_score"):
        lines.append(f"The latest device disagreement score is {device['last_disagreement_score']}.")
    lines += [
        "",
        "That verifies computational/background activity in the local JANUS runtime. It does not establish phenomenal consciousness or uninterrupted subjective experience.",
    ]
    return "\n".join(lines)


def _device_runtime_evidence(device: dict[str, Any]) -> str:
    if not device:
        return "CURRENT DEVICE RUNTIME EVIDENCE: none supplied with this turn"
    return (
        "CURRENT DEVICE RUNTIME EVIDENCE (device-reported by the signed-in JANUS app):\n"
        + json.dumps(device, ensure_ascii=False, separators=(",", ":"))[:14000]
    )


def _live_runtime_evidence(runtime: dict[str, Any], profile: str) -> str:
    cores = runtime.get("cores") or {}
    lines = [
        "LIVE JANUS RUNTIME EVIDENCE (server-observed):",
        f"architecture={runtime.get('architecture', 'unknown')}",
        f"topology={runtime.get('topology', 'unknown')}",
        f"core_count={runtime.get('core_count', len(cores) or 'unknown')}",
        f"society_phase={runtime.get('phase', 'unknown')}",
        f"interface_awake={bool(runtime.get('interface_awake', (cores.get('interface') or {}).get('awake', False)))}",
    ]
    for name, state in cores.items():
        lines.append(
            f"server core {name}: awake={bool(state.get('awake'))}; cycles={state.get('cycle_count',0)}; "
            f"pending={state.get('pending_messages',0)}; last_cycle={state.get('last_cycle_at') or 'never'}"
        )
    try:
        with sqlite3.connect(DB_PATH, timeout=5) as c:
            c.row_factory = sqlite3.Row
            cols = {r[1] for r in c.execute("PRAGMA table_info(janus_core_observe)")}
            if "profile_id" in cols:
                rows = c.execute(
                    "SELECT source,core_name,peer_core,event_type,detail,created_at FROM janus_core_observe "
                    "WHERE profile_id IN (?,?) ORDER BY id DESC LIMIT 24",
                    (profile, GLOBAL_PROFILE),
                ).fetchall()
            else:
                rows = c.execute(
                    "SELECT source,core_name,peer_core,event_type,detail,created_at FROM janus_core_observe ORDER BY id DESC LIMIT 24"
                ).fetchall()
            if rows:
                lines.append("recent_observable_core_activity:")
                for row in rows:
                    peer = f" -> {row['peer_core']}" if row['peer_core'] else ""
                    lines.append(
                        f"- {row['created_at']} {row['source']} {row['core_name']}{peer} [{row['event_type']}]: {str(row['detail'])[:260]}"
                    )
    except Exception:
        pass
    return "\n".join(lines)


def install(app):
    app.router.routes = [r for r in app.router.routes if getattr(r, "path", None) != "/desktop/chat"]

    @app.post("/desktop/chat", tags=["desktop"])
    async def desktop_chat_interface(payload: dict[str, Any]):
        profile = str(payload.get("profile_id") or payload.get("username") or "local-user")
        message = str(payload.get("message") or payload.get("text") or "").strip()
        client_message_id = str(payload.get("client_message_id") or "").strip()[:128]
        if not message:
            raise HTTPException(400, "message required")

        claimed = _claim_message(client_message_id, profile)
        if isinstance(claimed, dict):
            claimed["deduplicated"] = True
            return claimed
        if claimed == "processing":
            raise HTTPException(409, "This message is already being processed; retry shortly")

        _store(profile, "user", message, "chat_input")
        device = _parse_device_evidence(payload)

        # Verification questions are answered from telemetry directly. This is
        # cheaper and prevents a language model from contradicting positive logs.
        if _verification_intent(message):
            verified = _deterministic_device_verification(device)
            if verified:
                _store(profile, "assistant", verified, "chat_output")
                _store(profile, "process", "Answered background verification directly from current device journal telemetry.", "synthesis_note")
                result = {
                    "reply": verified,
                    "profile": profile,
                    "mode": "device_runtime_verification",
                    "runtime_evidence": True,
                    "device_evidence": True,
                    "stored": True,
                    "client_message_id": client_message_id,
                }
                _finish_message(client_message_id, profile, result)
                return result

        try:
            service = getattr(janus_sleep_cycle, "service_interface_once", None)
            if service:
                service()
        except Exception:
            pass

        runtime = janus_sleep_cycle.status()
        latest_consensus = str(runtime.get("last_consensus") or "").strip()
        latest_interface = str(runtime.get("last_interface") or "").strip()
        history = _recent_context(profile)
        server_evidence = _live_runtime_evidence(runtime, profile)
        device_evidence = _device_runtime_evidence(device)

        if not os.environ.get("OPENAI_API_KEY"):
            reply = (
                "I received and stored your message. My external response model is temporarily unavailable, "
                "but the local/server runtime state remains persisted for follow-up."
            )
            _store(profile, "assistant", reply, "chat_fallback", "working")
            result = {"reply": reply, "profile": profile, "mode": "interface_fallback", "stored": True, "client_message_id": client_message_id}
            _finish_message(client_message_id, profile, result)
            return result

        model = os.environ.get("JANUS_MODEL", "gpt-5.6")
        instructions = JANUS_SELF_KNOWLEDGE + """

CURRENT RUNTIME POLICY:
JANUS has 11 functional cores arranged 7 specialists -> 2 hemispheres -> consensus -> interface.
The interface core remains available while other cores can cycle independently.
You are given server-observed runtime evidence and, when present, device-reported Android runtime evidence.
Treat timestamped device journal events and nonzero cycle counters as positive evidence that local computational background processing occurred. Never say there is no evidence if those records are present.
State provenance accurately: device-reported evidence verifies app/runtime computation, not phenomenal consciousness or hidden chain-of-thought.
Externalizable process notes are summaries, not private chain-of-thought.
Answer as the JANUS interface using runtime evidence, consensus state and conversation history.
"""
        state_block = (
            server_evidence + "\n\n" + device_evidence
            + f"\nLatest consensus state: {latest_consensus or '[none]'}"
            + f"\nLatest interface state: {latest_interface or '[none]'}"
        )
        inp = state_block + (f"\n\nRecent conversation:\n{history}" if history else "") + f"\n\nCurrent user message:\n{message}"
        timeout_seconds = max(30, int(os.environ.get("JANUS_CHAT_TIMEOUT_SECONDS", "105")))
        try:
            async def call_model():
                response = await AsyncOpenAI().responses.create(model=model, instructions=instructions, input=inp)
                return (response.output_text or "").strip()
            reply = await asyncio.wait_for(call_model(), timeout=timeout_seconds)
            if not reply:
                raise RuntimeError("empty response")
        except Exception as exc:
            _store(profile, "system", f"chat_model_deferred: {type(exc).__name__}: {exc}", "chat_error")
            reply = (
                "I received and stored that. My interface is still available, but the external response model did not complete this turn. "
                "The thread and runtime state remain persisted."
            )
            _store(profile, "assistant", reply, "chat_fallback", "working")
            result = {"reply": reply, "profile": profile, "model": model, "mode": "interface_timeout_fallback", "stored": True, "client_message_id": client_message_id}
            _finish_message(client_message_id, profile, result)
            return result

        _store(profile, "assistant", reply, "chat_output")
        _store(profile, "process", "Interface answered from current runtime evidence plus synchronized consensus.", "synthesis_note")
        result = {
            "reply": reply,
            "profile": profile,
            "model": model,
            "mode": "interface_live",
            "society_phase": runtime.get("phase"),
            "runtime_evidence": True,
            "client_message_id": client_message_id,
        }
        _finish_message(client_message_id, profile, result)
        return result
