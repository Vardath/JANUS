"""One-time compatibility normalizer for legacy JANUS auth databases.

Runs before auth.py is imported. It preserves incompatible legacy auth tables,
creates the current account schema, and copies compatible account identity data.
No legacy table is dropped.
"""
from __future__ import annotations

import os
import re
import sqlite3
import time
from pathlib import Path

DB_PATH = Path(os.getenv("JANUS_AUTH_DB") or os.getenv("JANUS_DB_PATH") or "janus_auth.db")


def _table_exists(c: sqlite3.Connection, name: str) -> bool:
    return c.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def _columns(c: sqlite3.Connection, name: str) -> list[str]:
    if not _table_exists(c, name):
        return []
    return [str(row[1]) for row in c.execute(f'PRAGMA table_info("{name}")')]


def _legacy_name(c: sqlite3.Connection, table: str) -> str:
    base = f"{table}_legacy_normalized"
    name = base
    n = 2
    while _table_exists(c, name):
        name = f"{base}_{n}"
        n += 1
    return name


def _pick(row: sqlite3.Row, columns: set[str], *names: str, default=None):
    for name in names:
        if name in columns:
            value = row[name]
            if value is not None:
                return value
    return default


def _username_from(email: str, raw: str | None, used: set[str]) -> str:
    base = str(raw or email.split("@", 1)[0] or "janus").strip().lower()
    base = re.sub(r"[^a-z0-9._-]+", "-", base).strip("-._")[:24] or "janus"
    if len(base) < 3:
        base = (base + "janus")[:8]
    candidate = base
    n = 2
    while candidate.lower() in used:
        suffix = f"-{n}"
        candidate = f"{base[:32-len(suffix)]}{suffix}"
        n += 1
    used.add(candidate.lower())
    return candidate


def normalize_legacy_accounts() -> dict:
    """Normalize only when an existing accounts table lacks the current `id` key."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        c.execute("PRAGMA foreign_keys=OFF")
        cols = _columns(c, "accounts")
        if not cols or "id" in cols:
            return {"normalized": False, "reason": "current-or-new-schema"}

        # Preserve dependent legacy auth tables first. Renaming accounts while
        # old foreign keys are still active can make new sessions point at the
        # preserved legacy table instead of the normalized current table.
        preserved: dict[str, str] = {}
        for table in ("sessions", "auth_tokens"):
            if _table_exists(c, table):
                legacy = _legacy_name(c, table)
                c.execute(f'ALTER TABLE "{table}" RENAME TO "{legacy}"')
                preserved[table] = legacy

        legacy_accounts = _legacy_name(c, "accounts")
        c.execute(f'ALTER TABLE "accounts" RENAME TO "{legacy_accounts}"')
        preserved["accounts"] = legacy_accounts

        c.execute("""
            CREATE TABLE accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                disabled INTEGER NOT NULL DEFAULT 0,
                google_sub TEXT,
                email_verified INTEGER NOT NULL DEFAULT 0
            )
        """)

        legacy_cols = set(_columns(c, legacy_accounts))
        rows = c.execute(f'SELECT rowid AS __rowid__, * FROM "{legacy_accounts}"').fetchall()
        used_usernames: set[str] = set()
        used_emails: set[str] = set()
        copied = 0
        now = int(time.time())

        for row in rows:
            email = str(_pick(row, legacy_cols, "email", "email_address", default="") or "").strip().lower()
            if not email or "@" not in email or email in used_emails:
                continue
            used_emails.add(email)

            raw_username = _pick(row, legacy_cols, "username", "display_name", "name", default=None)
            username = _username_from(email, str(raw_username) if raw_username is not None else None, used_usernames)
            password_hash = str(_pick(row, legacy_cols, "password_hash", "password", default="legacy-no-password") or "legacy-no-password")
            created = int(_pick(row, legacy_cols, "created_at", "created", default=now) or now)
            updated = int(_pick(row, legacy_cols, "updated_at", "modified_at", default=created) or created)
            disabled = 1 if bool(_pick(row, legacy_cols, "disabled", "is_disabled", default=0)) else 0
            google_sub = _pick(row, legacy_cols, "google_sub", "google_id", default=None)
            email_verified = 1 if bool(_pick(row, legacy_cols, "email_verified", "verified", default=0)) else 0

            old_id = _pick(row, legacy_cols, "account_id", "user_id", default=None)
            try:
                old_id = int(old_id) if old_id is not None else None
                if old_id is not None and old_id <= 0:
                    old_id = None
            except Exception:
                old_id = None

            if old_id is None:
                c.execute(
                    "INSERT INTO accounts(username,email,password_hash,created_at,updated_at,disabled,google_sub,email_verified) VALUES(?,?,?,?,?,?,?,?)",
                    (username, email, password_hash, created, updated, disabled, google_sub, email_verified),
                )
            else:
                try:
                    c.execute(
                        "INSERT INTO accounts(id,username,email,password_hash,created_at,updated_at,disabled,google_sub,email_verified) VALUES(?,?,?,?,?,?,?,?,?)",
                        (old_id, username, email, password_hash, created, updated, disabled, google_sub, email_verified),
                    )
                except sqlite3.IntegrityError:
                    c.execute(
                        "INSERT INTO accounts(username,email,password_hash,created_at,updated_at,disabled,google_sub,email_verified) VALUES(?,?,?,?,?,?,?,?)",
                        (username, email, password_hash, created, updated, disabled, google_sub, email_verified),
                    )
            copied += 1

        c.commit()
        return {
            "normalized": True,
            "legacy_accounts": legacy_accounts,
            "preserved": preserved,
            "copied_accounts": copied,
        }
    finally:
        c.close()
