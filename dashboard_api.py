"""Dashboard/API compatibility layer for the JANUS desktop client.

The deployed service reconstructs ``server.py`` during the Render build. This
module imports that application and adds safe, read-only dashboard endpoints
without changing the compressed core source.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, Query

from server import app

DB_PATH = os.environ.get("JANUS_DB_PATH", "/data/janus.sqlite3")

SENSITIVE_PARTS = (
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "credential",
)
PROFILE_COLUMNS = ("username", "user", "profile_id", "owner", "account", "name")


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
    # A table without an ownership/profile column must not leak rows from other
    # users through the unauthenticated dashboard.
    return " WHERE 1=0", []


def _recent_rows(
    keywords: tuple[str, ...], profile: str | None, limit: int = 40
) -> dict[str, Any]:
    conn = _connect()
    if conn is None:
        return {"database": "unavailable", "tables": {}}
    try:
        output: dict[str, Any] = {}
        for table in _matching_tables(conn, keywords):
            cols = _columns(conn, table)
            where, params = _profile_clause(cols, profile)
            escaped = table.replace('"', '""')
            order_col = next(
                (
                    c
                    for c in cols
                    if c.lower()
                    in (
                        "updated_at",
                        "created_at",
                        "timestamp",
                        "time",
                        "ts",
                        "id",
                    )
                ),
                None,
            )
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
                counts[table] = int(
                    conn.execute(
                        f'SELECT COUNT(*) FROM "{escaped}"{where}', params
                    ).fetchone()[0]
                )
            except Exception:
                continue
        return counts
    finally:
        conn.close()


@app.get("/observe", tags=["dashboard"])
def dashboard_observe(username: str | None = Query(default=None)) -> dict[str, Any]:
    """Live high-level observation of the persistent JANUS process."""
    counts = _counts(username)
    return {
        "status": "online",
        "time_utc": _utc_now(),
        "profile": username or "unspecified",
        "architecture": "7 → 3 → 1",
        "persistent_store": "online" if os.path.exists(DB_PATH) else "initializing",
        "stored_rows_by_table": counts,
        "background_cycle": {
            "interval_minutes": int(os.environ.get("JANUS_INTERVAL_MINUTES", "15")),
            "dormancy_percent": int(os.environ.get("JANUS_DORMANCY_PERCENT", "67")),
            "self_evaluation": os.environ.get("JANUS_SELF_EVALUATION", "1") == "1",
            "memory_processing": os.environ.get("JANUS_MEMORY_PROCESSING", "1") == "1",
            "message_queue": os.environ.get("JANUS_MESSAGE_QUEUE", "1") == "1",
        },
    }


@app.get("/cores", tags=["dashboard"])
def dashboard_cores(username: str | None = Query(default=None)) -> dict[str, Any]:
    """Describe the active 7→3→1 JANUS core topology."""
    return {
        "status": "online",
        "profile": username or "unspecified",
        "topology": "7 → 3 → 1",
        "seven_roles": [
            "evidence",
            "logic",
            "counterpoint",
            "context",
            "memory",
            "safety",
            "novelty",
        ],
        "three_bridges": [
            "local synthesis",
            "global synthesis",
            "calibration / arbitration",
        ],
        "one_integrator": "JANUS integrated response",
        "runtime": {
            "model": os.environ.get("JANUS_MODEL", "configured by server"),
            "external_access": os.environ.get("JANUS_EXTERNAL_ACCESS", "1") == "1",
            "supervisor_consultation": os.environ.get("JANUS_SUPERVISOR_CONSULTATION", "0") == "1",
            "compute_budget": os.environ.get("JANUS_COMPUTE_BUDGET", "balanced"),
        },
        "note": "These are functional processing roles; this endpoint makes no claim of phenomenal consciousness.",
    }


@app.get("/memory", tags=["dashboard"])
def dashboard_memory(
    username: str | None = Query(default=None), limit: int = Query(default=40, ge=1, le=100)
) -> dict[str, Any]:
    """Return recent profile-scoped persistent memory records."""
    if not username:
        # The current desktop client first probes /memory and then retries with
        # ?username=. Reject the unscoped probe so no cross-profile data can be
        # returned and the client automatically performs its scoped retry.
        raise HTTPException(status_code=400, detail="profile scope required")
    data = _recent_rows(
        ("memory", "memories", "episod", "working", "trace", "identity", "core_memory"),
        username,
        limit,
    )
    return {
        "profile": username,
        "promotion_ladder": ["trace", "working", "episodic", "core"],
        **data,
    }


@app.get("/activity", tags=["dashboard"])
def dashboard_activity(
    username: str | None = Query(default=None), limit: int = Query(default=40, ge=1, le=100)
) -> dict[str, Any]:
    """Return recent profile-scoped background/activity records."""
    if not username:
        raise HTTPException(status_code=400, detail="profile scope required")
    data = _recent_rows(
        ("activity", "event", "history", "thought", "queue", "cycle", "audit", "log"),
        username,
        limit,
    )
    return {"profile": username, **data}


@app.get("/settings", tags=["dashboard"])
def dashboard_settings(username: str | None = Query(default=None)) -> dict[str, Any]:
    """Return non-secret runtime settings used by the JANUS global core."""
    return {
        "profile": username or "unspecified",
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
        "authentication": "Store/platform identity planned; JANUS desktop username/password gate disabled.",
    }
