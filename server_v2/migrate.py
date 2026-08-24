from __future__ import annotations

import datetime as dt
import sqlite3
from typing import Any

from . import storage


def _has_table(c: sqlite3.Connection, name: str) -> bool:
    return c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def _columns(c: sqlite3.Connection, name: str) -> set[str]:
    if not _has_table(c, name):
        return set()
    return {str(r[1]) for r in c.execute(f'PRAGMA table_info("{name}")')}


def _epoch(value: Any) -> int:
    if value is None:
        return storage.now()
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    try:
        return int(float(text))
    except Exception:
        pass
    try:
        return int(dt.datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp())
    except Exception:
        return storage.now()


def migrate_persistent_data_once() -> dict[str, int]:
    """Import durable user data into the new server schema once.

    No legacy application module is imported or executed. Only persisted rows are
    copied into the independently implemented v2 schema. Active session hashes are
    copied as data as well, so a signed-in native client can survive the server
    cutover without being forced to re-authenticate merely because orchestration
    was replaced.
    """
    counts = {"accounts": 0, "sessions": 0, "memories": 0, "events": 0}
    with storage.db() as c:
        existing = c.execute("SELECT count(*) FROM v2_accounts").fetchone()[0]
        if existing:
            return counts

        account_map: dict[str, int] = {}
        imported_ids: set[int] = set()
        cols = _columns(c, "accounts")
        if {"id", "username", "email", "password_hash"}.issubset(cols):
            select_cols = ["id", "username", "email", "password_hash"]
            select_cols += [x for x in ("google_sub", "email_verified", "created_at", "updated_at") if x in cols]
            for r in c.execute(f"SELECT {','.join(select_cols)} FROM accounts ORDER BY id"):
                d = dict(r)
                created = _epoch(d.get("created_at"))
                updated = _epoch(d.get("updated_at") or created)
                try:
                    aid = int(d["id"])
                    c.execute(
                        "INSERT INTO v2_accounts(id,username,email,password_hash,google_sub,email_verified,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                        (
                            aid, str(d["username"]), str(d["email"]).lower(), d.get("password_hash"),
                            d.get("google_sub"), int(d.get("email_verified") or 0), created, updated,
                        ),
                    )
                    account_map[str(d["username"]).lower()] = aid
                    imported_ids.add(aid)
                    counts["accounts"] += 1
                except sqlite3.IntegrityError:
                    pass

        # Preserve only active legacy sessions whose account was actually copied.
        # Both generations store SHA-256 token hashes, not bearer token plaintext.
        session_cols = _columns(c, "sessions")
        if imported_ids and {"token_hash", "account_id", "created_at", "expires_at"}.issubset(session_cols):
            now = storage.now()
            for r in c.execute("SELECT token_hash,account_id,created_at,expires_at FROM sessions WHERE expires_at>?", (now,)):
                d = dict(r)
                aid = int(d.get("account_id") or 0)
                if aid not in imported_ids:
                    continue
                try:
                    c.execute(
                        "INSERT OR IGNORE INTO v2_sessions(token_hash,account_id,created_at,expires_at) VALUES(?,?,?,?)",
                        (str(d["token_hash"]), aid, _epoch(d["created_at"]), _epoch(d["expires_at"])),
                    )
                    counts["sessions"] += int(c.execute("SELECT changes()").fetchone()[0] or 0)
                except (sqlite3.IntegrityError, ValueError, TypeError):
                    pass

        if _has_table(c, "desktop_memory") and account_map:
            cols = _columns(c, "desktop_memory")
            if {"profile_id", "content"}.issubset(cols):
                fields = [x for x in ("profile_id", "role", "content", "level", "created_at") if x in cols]
                for r in c.execute(f"SELECT {','.join(fields)} FROM desktop_memory ORDER BY id"):
                    d = dict(r)
                    aid = account_map.get(str(d.get("profile_id") or "").lower())
                    if not aid:
                        continue
                    content = str(d.get("content") or "").strip()
                    if not content:
                        continue
                    level = str(d.get("level") or "working").lower()
                    if level not in {"trace", "working", "episodic", "core"}:
                        level = "working"
                    stamp = _epoch(d.get("created_at"))
                    c.execute(
                        "INSERT INTO v2_memories(account_id,tier,kind,content,salience,access_count,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                        (aid, level, str(d.get("role") or "legacy_record")[:80], content[:20000], 0.55, 0, stamp, stamp),
                    )
                    counts["memories"] += 1

        if _has_table(c, "desktop_events") and account_map:
            cols = _columns(c, "desktop_events")
            if {"profile_id", "event_type", "detail"}.issubset(cols):
                fields = [x for x in ("profile_id", "event_type", "detail", "created_at") if x in cols]
                for r in c.execute(f"SELECT {','.join(fields)} FROM desktop_events ORDER BY id"):
                    d = dict(r)
                    aid = account_map.get(str(d.get("profile_id") or "").lower())
                    if not aid:
                        continue
                    detail = str(d.get("detail") or "").strip()
                    if not detail:
                        continue
                    c.execute(
                        "INSERT INTO v2_events(account_id,core_name,event_type,mode,detail,public_detail,created_at) VALUES(?,?,?,?,?,?,?)",
                        (aid, "memory", str(d.get("event_type") or "imported")[:80], "imported", detail[:50000], detail[:12000], _epoch(d.get("created_at"))),
                    )
                    counts["events"] += 1

    return counts
