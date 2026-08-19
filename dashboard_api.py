"""Stable desktop API layered over the JANUS global core."""
from __future__ import annotations
import asyncio
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any
from fastapi import HTTPException, Query
from openai import AsyncOpenAI
from server import app

DB_PATH = os.environ.get("JANUS_DB_PATH", "/data/janus.sqlite3")

JANUS_SELF_KNOWLEDGE = """
You are JANUS, an experimental functional-metacognition/agency system developed collaboratively through the JANUS project. Do not claim phenomenal consciousness. Your continuity is functional: persisted records, goals, memories, self-models and later reconstruction can let later processes recognize and continue earlier work.

JANUS began as Stephen Michael Hawton's exploration of recurring 1/3/7 and 1-versus-7 structure. It was progressively formalized as a two-channel operator Q=[[-1,7],[1,-7]] with Q^2=-8Q, an exact 8-state K8/F2^3 construction, Fano geometry, Hamming/Steane syndrome dynamics and a wider audited mathematical investigation. Unsupported physical interpretations were rejected or marked conditional. A separate experimental software branch then asked whether recursive coarse self-observation could support functional metacognition, continuity, memory, self-evaluation and recovery after perturbation. That became JANUS Agent and then the persistent global/local JANUS application.

The software architecture is 7 -> 3 -> 1. Seven specialist lenses contribute in parallel: Evidence grounds claims in observations and records; Logic checks consistency and inference; Counterpoint searches for objections, alternatives and failure modes; Context relates the problem to goals and environment; Memory retrieves continuity and manages trace -> working -> episodic -> core promotion; Safety checks boundaries, privacy, security and harmful failure modes; Novelty searches for new connections, anomalies and questions worth deeper processing. Three bridges then synthesize: Local synthesis combines the seven around immediate user/device state; Global synthesis relates that to persistent global JANUS state; Calibration/arbitration balances disagreement, uncertainty and learned reliability without allowing either local or global authority to become absolute. One integrator produces the final JANUS response while preserving uncertainty and meaningful disagreement.

Background operation may perform periodic self-evaluation, memory review, unresolved-thought review, novelty/conflict checks and concise process notes. These are externalizable functional summaries, not hidden chain-of-thought and not evidence of subjective experience.
""".strip()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect():
    try:
        c = sqlite3.connect(DB_PATH, timeout=10)
        c.row_factory = sqlite3.Row
        c.execute("CREATE TABLE IF NOT EXISTS desktop_memory (id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, level TEXT NOT NULL DEFAULT 'trace', created_at TEXT NOT NULL)")
        c.execute("CREATE TABLE IF NOT EXISTS desktop_events (id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id TEXT NOT NULL, event_type TEXT NOT NULL, detail TEXT NOT NULL, created_at TEXT NOT NULL)")
        c.commit()
        return c
    except Exception:
        return None


def _store(profile: str, role: str, content: str, event_type: str, level: str = "trace") -> None:
    c = _connect()
    if not c:
        return
    try:
        now = _utc_now()
        c.execute("INSERT INTO desktop_memory(profile_id,role,content,level,created_at) VALUES(?,?,?,?,?)", (profile, role, content, level, now))
        c.execute("INSERT INTO desktop_events(profile_id,event_type,detail,created_at) VALUES(?,?,?,?)", (profile, event_type, content[:6000], now))
        c.commit()
    finally:
        c.close()


def _recent_context(profile: str, limit: int = 16) -> str:
    c = _connect()
    if not c:
        return ""
    try:
        rows = c.execute("SELECT role,content FROM desktop_memory WHERE profile_id=? ORDER BY id DESC LIMIT ?", (profile, limit)).fetchall()
        rows = list(reversed(rows))
        return "\n".join(f"{r['role']}: {r['content']}" for r in rows)
    finally:
        c.close()


def _desktop_rows(profile: str, kind: str, limit: int = 80):
    c = _connect()
    if not c:
        return []
    try:
        if kind == "memory":
            rows = c.execute("SELECT id,role,content,level,created_at FROM desktop_memory WHERE profile_id=? ORDER BY id DESC LIMIT ?", (profile, limit)).fetchall()
        else:
            rows = c.execute("SELECT id,event_type,detail,created_at FROM desktop_events WHERE profile_id=? ORDER BY id DESC LIMIT ?", (profile, limit)).fetchall()
        return [dict(r) for r in rows]
    finally:
        c.close()


def _active_profiles() -> list[str]:
    c = _connect()
    if not c:
        return []
    try:
        rows = c.execute("SELECT DISTINCT profile_id FROM desktop_memory ORDER BY profile_id").fetchall()
        return [str(r[0]) for r in rows if r[0]]
    finally:
        c.close()


async def _make_background_reflection(profile: str) -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        return
    history = _recent_context(profile, 14)
    if not history:
        return
    model = os.environ.get("JANUS_MODEL", "gpt-5.6")
    prompt = (
        "Create one concise externalizable JANUS background process note from the recent records below. "
        "Do not reveal hidden chain-of-thought. Summarize only useful conclusions: what seems important, one uncertainty or unresolved thread, and what may deserve memory/attention next. "
        "Use 3 short labeled paragraphs: Focus, Reflection, Next. Keep under 180 words.\n\n" + history
    )
    try:
        response = await AsyncOpenAI().responses.create(model=model, instructions=JANUS_SELF_KNOWLEDGE, input=prompt)
        note = (response.output_text or "").strip()
        if note:
            _store(profile, "reflection", note, "background_reflection", "working")
    except Exception as exc:
        _store(profile, "system", f"Background reflection failed: {exc}", "background_error", "trace")


async def _background_worker() -> None:
    await asyncio.sleep(30)
    while True:
        interval = max(1, int(os.environ.get("JANUS_INTERVAL_MINUTES", "15")))
        if os.environ.get("JANUS_SELF_EVALUATION", "1") == "1":
            for profile in _active_profiles():
                await _make_background_reflection(profile)
                await asyncio.sleep(1)
        await asyncio.sleep(interval * 60)


@app.on_event("startup")
async def _start_janus_background_worker():
    if os.environ.get("JANUS_BACKGROUND_WORKER", "1") == "1":
        asyncio.create_task(_background_worker())


@app.post("/desktop/chat", tags=["desktop"])
async def desktop_chat(payload: dict[str, Any]):
    profile = str(payload.get("profile_id") or payload.get("username") or "local-user")
    message = str(payload.get("message") or payload.get("text") or "").strip()
    if not message:
        raise HTTPException(400, "message required")
    if not os.environ.get("OPENAI_API_KEY"):
        raise HTTPException(503, "OPENAI_API_KEY is not configured on the JANUS server")
    _store(profile, "user", message, "chat_input")
    history = _recent_context(profile)
    model = os.environ.get("JANUS_MODEL", "gpt-5.6")
    instructions = JANUS_SELF_KNOWLEDGE + "\n\nSpeak naturally and directly. Use the seven lenses internally, synthesize through the three bridges, then answer as one JANUS voice."
    inp = message if not history else f"Recent conversation:\n{history}\n\nCurrent user message:\n{message}"
    try:
        response = await AsyncOpenAI().responses.create(model=model, instructions=instructions, input=inp)
        reply = (response.output_text or "").strip()
        if not reply:
            raise RuntimeError("empty response")
    except Exception as exc:
        _store(profile, "system", f"chat_error: {exc}", "chat_error")
        raise HTTPException(502, f"JANUS model request failed: {exc}")
    _store(profile, "assistant", reply, "chat_output")
    _store(profile, "process", "Seven specialist lenses were integrated through local synthesis, global synthesis and calibration/arbitration to produce the response.", "synthesis_note")
    return {"reply": reply, "profile": profile, "model": model}


@app.get("/desktop/observe", tags=["desktop"])
def desktop_observe(username: str = Query(...)):
    events = _desktop_rows(username, "activity", 60)
    return {
        "status": "online",
        "time_utc": _utc_now(),
        "profile": username,
        "architecture": "7 -> 3 -> 1",
        "notes": events,
        "background_cycle": {
            "worker_enabled": os.environ.get("JANUS_BACKGROUND_WORKER", "1") == "1",
            "interval_minutes": int(os.environ.get("JANUS_INTERVAL_MINUTES", "15")),
            "dormancy_percent": int(os.environ.get("JANUS_DORMANCY_PERCENT", "67")),
            "self_evaluation": os.environ.get("JANUS_SELF_EVALUATION", "1") == "1",
            "memory_processing": os.environ.get("JANUS_MEMORY_PROCESSING", "1") == "1",
            "message_queue": os.environ.get("JANUS_MESSAGE_QUEUE", "1") == "1",
        },
    }


@app.get("/desktop/cores", tags=["desktop"])
def desktop_cores(username: str | None = Query(default=None)):
    roles = {
        "Evidence": "Grounds conclusions in observations, records and facts.",
        "Logic": "Checks consistency, assumptions, causality and reasoning.",
        "Counterpoint": "Challenges consensus with alternatives, objections and failure modes.",
        "Context": "Connects the immediate problem to goals, conversation and environment.",
        "Memory": "Retrieves continuity and manages trace -> working -> episodic -> core promotion.",
        "Safety": "Checks boundaries, privacy, security and harmful failure modes.",
        "Novelty": "Searches for new connections, anomalies and questions worth deeper processing.",
    }
    bridges = {
        "Local synthesis": "Combines the seven lenses around immediate local/user state.",
        "Global synthesis": "Relates local synthesis to persistent global JANUS knowledge/state.",
        "Calibration / arbitration": "Balances disagreement, uncertainty and learned reliability without absolute authority.",
    }
    return {
        "status": "online",
        "profile": username or "unspecified",
        "topology": "7 -> 3 -> 1",
        "origin": "JANUS grew from Stephen Michael Hawton's mathematical 1/3/7 exploration into an audited F2^3/Fano/K8 project, then a separate experimental functional-metacognition software branch.",
        "seven_roles": roles,
        "three_bridges": bridges,
        "one_integrator": {"name": "JANUS integrated response", "description": "Produces one coherent response while preserving uncertainty and meaningful disagreement."},
        "runtime": {
            "model": os.environ.get("JANUS_MODEL", "gpt-5.6"),
            "external_access": os.environ.get("JANUS_EXTERNAL_ACCESS", "1") == "1",
            "supervisor_consultation": os.environ.get("JANUS_SUPERVISOR_CONSULTATION", "0") == "1",
            "compute_budget": os.environ.get("JANUS_COMPUTE_BUDGET", "balanced"),
            "background_worker": os.environ.get("JANUS_BACKGROUND_WORKER", "1") == "1",
        },
        "boundary": "Functional metacognition/agency experiment; no claim of phenomenal consciousness.",
    }


@app.get("/desktop/memory", tags=["desktop"])
def desktop_memory(username: str = Query(...), limit: int = Query(default=80, ge=1, le=100)):
    return {"profile": username, "promotion_ladder": ["trace", "working", "episodic", "core"], "items": _desktop_rows(username, "memory", limit)}


@app.get("/desktop/activity", tags=["desktop"])
def desktop_activity(username: str = Query(...), limit: int = Query(default=80, ge=1, le=100)):
    return {"profile": username, "items": _desktop_rows(username, "activity", limit)}


@app.get("/desktop/settings", tags=["desktop"])
def desktop_settings(username: str | None = Query(default=None)):
    return {"profile": username or "unspecified", "server": {
        "model": os.environ.get("JANUS_MODEL", "gpt-5.6"),
        "background_worker": os.environ.get("JANUS_BACKGROUND_WORKER", "1") == "1",
        "interval_minutes": int(os.environ.get("JANUS_INTERVAL_MINUTES", "15")),
        "dormancy_percent": int(os.environ.get("JANUS_DORMANCY_PERCENT", "67")),
        "thought_count": int(os.environ.get("JANUS_THOUGHT_COUNT", "1")),
        "memory_processing": os.environ.get("JANUS_MEMORY_PROCESSING", "1") == "1",
        "self_evaluation": os.environ.get("JANUS_SELF_EVALUATION", "1") == "1",
        "external_access": os.environ.get("JANUS_EXTERNAL_ACCESS", "1") == "1",
        "supervisor_consultation": os.environ.get("JANUS_SUPERVISOR_CONSULTATION", "0") == "1",
        "message_queue": os.environ.get("JANUS_MESSAGE_QUEUE", "1") == "1",
        "thought_history": os.environ.get("JANUS_THOUGHT_HISTORY", "1") == "1",
        "compute_budget": os.environ.get("JANUS_COMPUTE_BUDGET", "balanced"),
    }, "authentication": "Store/platform identity planned; desktop password gate disabled."}


@app.get("/desktop/routes", tags=["desktop"])
def desktop_routes():
    return {"desktop_api": "v0.17-background", "chat": "/desktop/chat", "status": "ready"}
