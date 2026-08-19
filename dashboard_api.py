"""Stable desktop API layered over the JANUS global core.

This module keeps the existing reconstructed server app, while providing a
stable API for desktop/mobile clients. Desktop chat uses the configured OpenAI
API key directly so it cannot hang on historical internal route discovery.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, Query
from openai import AsyncOpenAI

from server import app

DB_PATH = os.environ.get("JANUS_DB_PATH", "/data/janus.sqlite3")
PROFILE_COLUMNS = ("username", "user", "profile_id", "owner", "account", "name")
SENSITIVE_PARTS = ("password", "secret", "token", "api_key", "apikey", "authorization", "credential")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_desktop_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS desktop_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            level TEXT NOT NULL DEFAULT 'trace',
            created_at TEXT NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS desktop_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            detail TEXT NOT NULL,
            created_at TEXT NOT NULL
        )"""
    )
    conn.commit()


def _connect() -> sqlite3.Connection | None:
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.row_factory = sqlite3.Row
        _ensure_desktop_tables(conn)
        return conn
    except Exception:
        return None


def _safe_value(name: str, value: Any) -> Any:
    if any(part in name.lower() for part in SENSITIVE_PARTS):
        return "[redacted]"
    if isinstance(value, bytes):
        return f"<bytes:{len(value)}>"
    if isinstance(value, str) and len(value) > 4000:
        return value[:4000] + "…"
    return value


def _tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
    return [str(r[0]) for r in rows]


def _columns(conn: sqlite3.Connection, table: str) -> list[str]:
    escaped = table.replace('"', '""')
    return [str(r[1]) for r in conn.execute(f'PRAGMA table_info("{escaped}")').fetchall()]


def _profile_clause(columns: list[str], profile: str | None) -> tuple[str, list[Any]]:
    if not profile:
        return " WHERE 1=0", []
    by_lower = {c.lower(): c for c in columns}
    for candidate in PROFILE_COLUMNS:
        if candidate in by_lower:
            actual = by_lower[candidate].replace('"', '""')
            return f' WHERE "{actual}" = ?', [profile]
    return " WHERE 1=0", []


def _matching_tables(conn: sqlite3.Connection, keywords: tuple[str, ...]) -> list[str]:
    out = []
    for table in _tables(conn):
        text = (table + " " + " ".join(_columns(conn, table))).lower()
        if any(k in text for k in keywords):
            out.append(table)
    return out


def _recent_rows(keywords: tuple[str, ...], profile: str | None, limit: int = 40) -> dict[str, Any]:
    conn = _connect()
    if conn is None:
        return {"database": "unavailable", "tables": {}}
    try:
        output: dict[str, Any] = {}
        for table in _matching_tables(conn, keywords):
            cols = _columns(conn, table)
            where, params = _profile_clause(cols, profile)
            escaped = table.replace('"', '""')
            order_col = next((c for c in cols if c.lower() in ("updated_at", "created_at", "timestamp", "time", "ts", "id")), None)
            order = ""
            if order_col:
                safe_order = order_col.replace('"', '""')
                order = f' ORDER BY "{safe_order}" DESC'
            rows = conn.execute(f'SELECT * FROM "{escaped}"{where}{order} LIMIT ?', [*params, max(1, min(limit, 100))]).fetchall()
            output[table] = [{k: _safe_value(k, row[k]) for k in row.keys()} for row in rows]
        return {"database": "online", "tables": output}
    except Exception as exc:
        return {"database": "error", "error": str(exc), "tables": {}}
    finally:
        conn.close()


def _counts(profile: str | None) -> dict[str, int]:
    conn = _connect()
    if conn is None:
        return {}
    try:
        counts: dict[str, int] = {}
        for table in _tables(conn):
            cols = _columns(conn, table)
            where, params = _profile_clause(cols, profile)
            escaped = table.replace('"', '""')
            try:
                counts[table] = int(conn.execute(f'SELECT COUNT(*) FROM "{escaped}"{where}', params).fetchone()[0])
            except Exception:
                pass
        return counts
    finally:
        conn.close()


def _store(profile: str, role: str, content: str, event_type: str) -> None:
    conn = _connect()
    if conn is None:
        return
    try:
        now = _utc_now()
        conn.execute(
            "INSERT INTO desktop_memory(profile_id, role, content, level, created_at) VALUES(?,?,?,?,?)",
            (profile, role, content, "trace", now),
        )
        conn.execute(
            "INSERT INTO desktop_events(profile_id, event_type, detail, created_at) VALUES(?,?,?,?)",
            (profile, event_type, content[:2000], now),
        )
        conn.commit()
    finally:
        conn.close()


def _recent_context(profile: str, limit: int = 12) -> str:
    conn = _connect()
    if conn is None:
        return ""
    try:
        rows = conn.execute(
            "SELECT role, content FROM desktop_memory WHERE profile_id=? ORDER BY id DESC LIMIT ?",
            (profile, limit),
        ).fetchall()
        rows = list(reversed(rows))
        return "\n".join(f"{r['role']}: {r['content']}" for r in rows)
    finally:
        conn.close()


@app.post("/desktop/chat", tags=["desktop"])
async def desktop_chat(payload: dict[str, Any]) -> dict[str, Any]:
    profile = str(payload.get("profile_id") or payload.get("username") or payload.get("user") or "local-user")
    message = str(payload.get("message") or payload.get("text") or payload.get("prompt") or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="message required")
    if not os.environ.get("OPENAI_API_KEY"):
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured on the JANUS server")

    _store(profile, "user", message, "chat_input")
    history = _recent_context(profile)
    model = os.environ.get("JANUS_MODEL", "gpt-5.6")

    instructions = (
        "You are JANUS, an experimental functional-metacognition and agency system. "
        "Use a 7→3→1 internal architecture: seven lenses (evidence, logic, counterpoint, context, memory, safety, novelty), "
        "three synthesis bridges (local synthesis, global synthesis, calibration/arbitration), then one integrated response. "
        "Do not claim phenomenal consciousness. Speak naturally and directly to the user. Preserve continuity from the supplied recent history when useful."
    )
    user_input = message if not history else f"Recent JANUS conversation history:\n{history}\n\nCurrent user message:\n{message}"

    try:
        client = AsyncOpenAI()
        response = await client.responses.create(model=model, instructions=instructions, input=user_input)
        reply = (response.output_text or "").strip()
        if not reply:
            raise RuntimeError("OpenAI returned an empty response")
    except Exception as exc:
        _store(profile, "system", f"chat_error: {exc}", "chat_error")
        raise HTTPException(status_code=502, detail=f"JANUS model request failed: {exc}")

    _store(profile, "assistant", reply, "chat_output")
    return {"reply": reply, "profile": profile, "model": model}


@app.get("/desktop/observe", tags=["desktop"])
def desktop_observe(username: str | None = Query(default=None)) -> dict[str, Any]:
    return {
        "status": "online",
        "time_utc": _utc_now(),
        "profile": username or "unspecified",
        "architecture": "7 → 3 → 1",
        "persistent_store": "online" if os.path.exists(DB_PATH) else "initializing",
        "stored_rows_by_table": _counts(username),
        "background_cycle": {
            "interval_minutes": int(os.environ.get("JANUS_INTERVAL_MINUTES", "15")),
            "dormancy_percent": int(os.environ.get("JANUS_DORMANCY_PERCENT", "67")),
            "self_evaluation": os.environ.get("JANUS_SELF_EVALUATION", "1") == "1",
            "memory_processing": os.environ.get("JANUS_MEMORY_PROCESSING", "1") == "1",
            "message_queue": os.environ.get("JANUS_MESSAGE_QUEUE", "1") == "1",
        },
    }


@app.get("/desktop/cores", tags=["desktop"])
def desktop_cores(username: str | None = Query(default=None)) -> dict[str, Any]:
    return {
        "status": "online",
        "profile": username or "unspecified",
        "topology": "7 → 3 → 1",
        "seven_roles": ["evidence", "logic", "counterpoint", "context", "memory", "safety", "novelty"],
        "three_bridges": ["local synthesis", "global synthesis", "calibration / arbitration"],
        "one_integrator": "JANUS integrated response",
        "runtime": {
            "model": os.environ.get("JANUS_MODEL", "gpt-5.6"),
            "external_access": os.environ.get("JANUS_EXTERNAL_ACCESS", "1") == "1",
            "supervisor_consultation": os.environ.get("JANUS_SUPERVISOR_CONSULTATION", "0") == "1",
            "compute_budget": os.environ.get("JANUS_COMPUTE_BUDGET", "balanced"),
        },
        "note": "Functional processing roles; no claim of phenomenal consciousness.",
    }


@app.get("/desktop/memory", tags=["desktop"])
def desktop_memory(username: str = Query(...), limit: int = Query(default=40, ge=1, le=100)) -> dict[str, Any]:
    return {
        "profile": username,
        "promotion_ladder": ["trace", "working", "episodic", "core"],
        **_recent_rows(("memory", "memories", "episod", "working", "trace", "identity", "core_memory"), username, limit),
    }


@app.get("/desktop/activity", tags=["desktop"])
def desktop_activity(username: str = Query(...), limit: int = Query(default=40, ge=1, le=100)) -> dict[str, Any]:
    return {
        "profile": username,
        **_recent_rows(("activity", "event", "history", "thought", "queue", "cycle", "audit", "log"), username, limit),
    }


@app.get("/desktop/settings", tags=["desktop"])
def desktop_settings(username: str | None = Query(default=None)) -> dict[str, Any]:
    return {
        "profile": username or "unspecified",
        "server": {
            "model": os.environ.get("JANUS_MODEL", "gpt-5.6"),
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
        },
        "authentication": "Store/platform identity planned; desktop password gate disabled.",
    }


@app.get("/desktop/routes", tags=["desktop"])
def desktop_routes() -> dict[str, Any]:
    return {"desktop_api": "v0.13-direct", "chat": "/desktop/chat", "status": "ready"}
