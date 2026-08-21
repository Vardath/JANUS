"""Pre-import auth schema guard for JANUS Render persistence.

Handles legacy tables that look partly current (for example, sessions has
account_id) but are still missing columns required by the current auth code.
No legacy table is deleted; incompatible tables are renamed and auth.py creates
fresh current tables afterwards.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.getenv("JANUS_AUTH_DB") or os.getenv("JANUS_DB_PATH") or "janus_auth.db")


def _exists(c: sqlite3.Connection, name: str) -> bool:
    return c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def _columns(c: sqlite3.Connection, name: str) -> set[str]:
    if not _exists(c, name):
        return set()
    return {str(row[1]) for row in c.execute(f'PRAGMA table_info("{name}")')}


def _legacy_name(c: sqlite3.Connection, table: str) -> str:
    base = f"{table}_legacy_guard"
    name = base
    n = 2
    while _exists(c, name):
        name = f"{base}_{n}"
        n += 1
    return name


def guard_auth_schema() -> dict:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    try:
        c.execute("PRAGMA foreign_keys=OFF")
        actions: list[str] = []

        # accounts is usually already normalized by auth_db_normalizer. These
        # columns can be added safely to partially-current schemas.
        if _exists(c, "accounts"):
            cols = _columns(c, "accounts")
            if "disabled" not in cols:
                c.execute("ALTER TABLE accounts ADD COLUMN disabled INTEGER NOT NULL DEFAULT 0")
                actions.append("accounts:+disabled")
            if "google_sub" not in cols:
                c.execute("ALTER TABLE accounts ADD COLUMN google_sub TEXT")
                actions.append("accounts:+google_sub")
            if "email_verified" not in cols:
                c.execute("ALTER TABLE accounts ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 0")
                actions.append("accounts:+email_verified")
            if "updated_at" not in cols:
                c.execute("ALTER TABLE accounts ADD COLUMN updated_at INTEGER NOT NULL DEFAULT 0")
                if "created_at" in cols:
                    c.execute("UPDATE accounts SET updated_at=created_at WHERE updated_at=0")
                actions.append("accounts:+updated_at")

        required = {
            "sessions": {"token_hash", "account_id", "created_at", "expires_at"},
            "auth_tokens": {"token_hash", "account_id", "purpose", "created_at", "expires_at", "used_at"},
        }
        preserved: dict[str, str] = {}
        for table, needed in required.items():
            if not _exists(c, table):
                continue
            cols = _columns(c, table)
            if not needed.issubset(cols):
                legacy = _legacy_name(c, table)
                c.execute(f'ALTER TABLE "{table}" RENAME TO "{legacy}"')
                preserved[table] = legacy
                actions.append(f"{table}:preserved-as:{legacy}")

        c.commit()
        return {
            "ok": True,
            "database": str(DB_PATH),
            "actions": actions,
            "preserved": preserved,
        }
    finally:
        c.close()


def auth_schema_snapshot() -> dict:
    c = sqlite3.connect(DB_PATH)
    try:
        tables = {}
        for name in ("accounts", "sessions", "auth_tokens"):
            tables[name] = sorted(_columns(c, name)) if _exists(c, name) else []
        return {"database": str(DB_PATH), "tables": tables}
    finally:
        c.close()
