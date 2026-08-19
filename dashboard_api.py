"""Stable desktop API layered over the JANUS global core.

Render reconstructs ``server.py`` during deploy.  This module imports that app,
keeps the existing core untouched, then adds stable endpoints used by the
Windows/mobile clients.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, Query, Request
from fastapi.routing import APIRoute
from starlette.responses import Response

from server import app

DB_PATH = os.environ.get("JANUS_DB_PATH", "/data/janus.sqlite3")
SENSITIVE_PARTS = (
    "password", "secret", "token", "api_key", "apikey", "authorization",
    "credential",
)
PROFILE_COLUMNS = ("username", "user", "profile_id", "owner", "account", "name")

# Capture core routes before adding the compatibility layer so /desktop/chat can
# forward to the real JANUS conversational endpoint without knowing its exact
# historical path in advance.
CORE_ROUTES = list(app.router.routes)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection | None:
    try:
        if not os.path.exists(DB_PATH):
            return None
        conn = sqlite3.connect(DB_PATH, timeout=5)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception:
        return None


def _safe_value(name: str, value: Any) -> Any:
    low = name.lower()
    if any(part in low for part in SENSITIVE_PARTS):
        return "[redacted]"
    if isinstance(value, bytes):
        return f"<bytes:{len(value)}>"
    if isinstance(value, str) and len(value) > 4000:
        return value[:4000] + "…"
    return value


def _tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [str(r[0]) for r in rows]


def _columns(conn: sqlite3.Connection, table: str) -> list[str]:
    escaped = table.replace('"', '""')
    return [str(r[1]) for r in conn.execute(f'PRAGMA table_info("{escaped}")').fetchall()]


def _matching_tables(conn: sqlite3.Connection, keywords: tuple[str, ...]) -> list[str]:
    result: list[str] = []
    for table in _tables(conn):
        text = table.lower()
        cols = " ".join(_columns(conn, table)).lower()
        if any(k in text or k in cols for k in keywords):
            result.append(table)
    return result


def _profile_clause(columns: list[str], profile: str | None) -> tuple[str, list[Any]]:
    if not profile:
        return " WHERE 1=0", []
    by_lower = {c.lower(): c for c in columns}
    for candidate in PROFILE_COLUMNS:
        if candidate in by_lower:
            actual = by_lower[candidate].replace('"', '""')
            return f' WHERE "{actual}" = ?', [profile]
    return " WHERE 1=0", []


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
            order_col = next((c for c in cols if c.lower() in (
                "updated_at", "created_at", "timestamp", "time", "ts", "id"
            )), None)
            order = ""
            if order_col:
                safe_order = order_col.replace('"', '""')
                order = f' ORDER BY "{safe_order}" DESC'
            sql = f'SELECT * FROM "{escaped}"{where}{order} LIMIT ?'
            rows = conn.execute(sql, [*params, max(1, min(limit, 100))]).fetchall()
            output[table] = [
                {k: _safe_value(k, row[k]) for k in row.keys()} for row in rows
            ]
        return {"database": "online", "tables": output}
    except Exception as exc:
        return {"database": "error", "error": str(exc), "tables": {}}
    finally:
        conn.close()


def _counts(profile: str | None) -> dict[str, int]:
    conn = _connect()
    if conn is None:
        return {}
    counts: dict[str, int] = {}
    try:
        for table in _tables(conn):
            cols = _columns(conn, table)
            where, params = _profile_clause(cols, profile)
            escaped = table.replace('"', '""')
            try:
                counts[table] = int(conn.execute(
                    f'SELECT COUNT(*) FROM "{escaped}"{where}', params
                ).fetchone()[0])
            except Exception:
                continue
        return counts
    finally:
        conn.close()


def _observe(profile: str | None) -> dict[str, Any]:
    return {
        "status": "online",
        "time_utc": _utc_now(),
        "profile": profile or "unspecified",
        "architecture": "7 → 3 → 1",
        "persistent_store": "online" if os.path.exists(DB_PATH) else "initializing",
        "stored_rows_by_table": _counts(profile),
        "background_cycle": {
            "interval_minutes": int(os.environ.get("JANUS_INTERVAL_MINUTES", "15")),
            "dormancy_percent": int(os.environ.get("JANUS_DORMANCY_PERCENT", "67")),
            "self_evaluation": os.environ.get("JANUS_SELF_EVALUATION", "1") == "1",
            "memory_processing": os.environ.get("JANUS_MEMORY_PROCESSING", "1") == "1",
            "message_queue": os.environ.get("JANUS_MESSAGE_QUEUE", "1") == "1",
        },
    }


def _cores(profile: str | None) -> dict[str, Any]:
    return {
        "status": "online",
        "profile": profile or "unspecified",
        "topology": "7 → 3 → 1",
        "seven_roles": [
            "evidence", "logic", "counterpoint", "context", "memory", "safety", "novelty"
        ],
        "three_bridges": [
            "local synthesis", "global synthesis", "calibration / arbitration"
        ],
        "one_integrator": "JANUS integrated response",
        "runtime": {
            "model": os.environ.get("JANUS_MODEL", "configured by server"),
            "external_access": os.environ.get("JANUS_EXTERNAL_ACCESS", "1") == "1",
            "supervisor_consultation": os.environ.get("JANUS_SUPERVISOR_CONSULTATION", "0") == "1",
            "compute_budget": os.environ.get("JANUS_COMPUTE_BUDGET", "balanced"),
        },
        "note": "Functional processing roles; no claim of phenomenal consciousness.",
    }


def _settings(profile: str | None) -> dict[str, Any]:
    return {
        "profile": profile or "unspecified",
        "server": {
            "model": os.environ.get("JANUS_MODEL", "configured by server"),
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


def _core_post_routes() -> list[APIRoute]:
    scored: list[tuple[int, APIRoute]] = []
    words = {
        "chat": 12, "conversation": 11, "message": 10, "turn": 9,
        "interact": 8, "respond": 7, "prompt": 6, "talk": 6,
    }
    for route in CORE_ROUTES:
        if not isinstance(route, APIRoute) or "POST" not in (route.methods or set()):
            continue
        if "{" in route.path or route.path.startswith(("/auth", "/admin")):
            continue
        text = (route.path + " " + route.name).lower()
        score = sum(weight for word, weight in words.items() if word in text)
        if score:
            scored.append((score, route))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored]


def _adapt_payload(route: APIRoute, profile: str, message: str) -> dict[str, Any]:
    # Infer the body model fields when possible. This lets the stable desktop
    # endpoint survive historical core schemas such as username/message,
    # user/text, profile_id/prompt, etc.
    body = getattr(route, "body_field", None)
    model = getattr(body, "type_", None) or getattr(body, "annotation", None)
    fields = getattr(model, "model_fields", None) or getattr(model, "__fields__", None)
    if not fields:
        return {"username": profile, "message": message}
    payload: dict[str, Any] = {}
    for name, field in fields.items():
        low = name.lower()
        if any(k in low for k in ("username", "profile", "user_id", "userid", "owner", "account", "name")):
            payload[name] = profile
        elif any(k in low for k in ("message", "text", "prompt", "input", "query", "content")):
            payload[name] = message
        else:
            default = getattr(field, "default", None)
            required = getattr(field, "is_required", lambda: False)()
            if not required and default is not None:
                payload[name] = default
    return payload or {"username": profile, "message": message}


async def _invoke_core_route(route: APIRoute, request: Request, payload: dict[str, Any]) -> Response:
    body = json.dumps(payload).encode("utf-8")
    scope = dict(request.scope)
    scope["path"] = route.path
    scope["raw_path"] = route.path.encode("utf-8")
    scope["query_string"] = b""

    # Desktop has no JANUS password gate. Authenticate this server-local bridge
    # to protected core routes with Render's private service token instead.
    headers = [(k.lower(), v) for k, v in scope.get("headers", []) if k.lower() not in (
        b"content-length", b"authorization", b"x-access-token"
    )]
    token = os.environ.get("JANUS_ACCESS_TOKEN", "")
    if token:
        headers.append((b"authorization", f"Bearer {token}".encode("utf-8")))
        headers.append((b"x-access-token", token.encode("utf-8")))
    headers.append((b"content-type", b"application/json"))
    headers.append((b"content-length", str(len(body)).encode("ascii")))
    scope["headers"] = headers

    sent = False
    async def receive():
        nonlocal sent
        if sent:
            return {"type": "http.request", "body": b"", "more_body": False}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    messages: list[dict[str, Any]] = []
    async def send(message_obj):
        messages.append(message_obj)

    await route.handle(scope, receive, send)
    start = next((m for m in messages if m.get("type") == "http.response.start"), {})
    chunks = [m.get("body", b"") for m in messages if m.get("type") == "http.response.body"]
    status = int(start.get("status", 500))
    out_headers = {}
    for k, v in start.get("headers", []):
        key = k.decode("latin-1")
        if key.lower() not in ("content-length", "content-encoding", "transfer-encoding"):
            out_headers[key] = v.decode("latin-1")
    return Response(content=b"".join(chunks), status_code=status, headers=out_headers)


@app.post("/desktop/chat", tags=["desktop"])
async def desktop_chat(request: Request) -> Response:
    data = await request.json()
    profile = str(data.get("profile_id") or data.get("username") or data.get("user") or "local-user")
    message = str(data.get("message") or data.get("text") or data.get("prompt") or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="message required")

    candidates = _core_post_routes()
    if not candidates:
        raise HTTPException(status_code=503, detail="No JANUS conversational core route is available")

    last_response: Response | None = None
    for route in candidates:
        payload = _adapt_payload(route, profile, message)
        response = await _invoke_core_route(route, request, payload)
        last_response = response
        # Schema/path mismatch responses are safe to try against the next known
        # conversational route. Any other response came from the core itself.
        if response.status_code not in (404, 405, 422):
            return response
    return last_response or Response(
        content=b'{"detail":"JANUS conversational route unavailable"}',
        status_code=503,
        media_type="application/json",
    )


@app.get("/desktop/observe", tags=["desktop"])
def desktop_observe(username: str | None = Query(default=None)) -> dict[str, Any]:
    return _observe(username)


@app.get("/desktop/cores", tags=["desktop"])
def desktop_cores(username: str | None = Query(default=None)) -> dict[str, Any]:
    return _cores(username)


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
    return _settings(username)


@app.get("/desktop/routes", tags=["desktop"])
def desktop_routes() -> dict[str, Any]:
    """Non-secret route diagnostics for client compatibility troubleshooting."""
    return {
        "core_post_candidates": [r.path for r in _core_post_routes()],
        "desktop_api": "v0.12",
    }

# Legacy aliases retained for older clients. Stable clients should use /desktop/*.
@app.get("/observe", tags=["dashboard"])
def dashboard_observe(username: str | None = Query(default=None)) -> dict[str, Any]:
    return _observe(username)

@app.get("/cores", tags=["dashboard"])
def dashboard_cores(username: str | None = Query(default=None)) -> dict[str, Any]:
    return _cores(username)

@app.get("/memory", tags=["dashboard"])
def dashboard_memory(username: str = Query(...), limit: int = Query(default=40, ge=1, le=100)) -> dict[str, Any]:
    return desktop_memory(username, limit)

@app.get("/activity", tags=["dashboard"])
def dashboard_activity(username: str = Query(...), limit: int = Query(default=40, ge=1, le=100)) -> dict[str, Any]:
    return desktop_activity(username, limit)

@app.get("/settings", tags=["dashboard"])
def dashboard_settings(username: str | None = Query(default=None)) -> dict[str, Any]:
    return _settings(username)
