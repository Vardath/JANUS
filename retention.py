"""JANUS retention policy enforcement.

User conversation/memory/activity content is retained until account deletion because
continuity is a core feature. Security/temporary records have shorter retention.
"""
from __future__ import annotations

import asyncio
import os
import time

import auth

AUTH_TOKEN_CLEANUP_DAYS = max(1, int(os.getenv("JANUS_AUTH_TOKEN_CLEANUP_DAYS", "7")))
DELETION_REQUEST_RETENTION_DAYS = max(1, int(os.getenv("JANUS_DELETION_REQUEST_RETENTION_DAYS", "90")))


def cleanup_once() -> dict[str, int]:
    now = int(time.time())
    token_cutoff = now - AUTH_TOKEN_CLEANUP_DAYS * 86400
    deletion_cutoff = now - DELETION_REQUEST_RETENTION_DAYS * 86400
    counts = {"sessions": 0, "auth_tokens": 0, "deletion_requests": 0}
    with auth._db() as c:
        cur = c.execute("DELETE FROM sessions WHERE expires_at<=?", (now,))
        counts["sessions"] = max(0, cur.rowcount)
        cur = c.execute(
            "DELETE FROM auth_tokens WHERE expires_at<=? OR (used_at IS NOT NULL AND used_at<=?)",
            (now, token_cutoff),
        )
        counts["auth_tokens"] = max(0, cur.rowcount)
        exists = c.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='account_deletion_requests'"
        ).fetchone()
        if exists:
            cur = c.execute(
                "DELETE FROM account_deletion_requests WHERE requested_at<=? AND status='pending'",
                (deletion_cutoff,),
            )
            counts["deletion_requests"] = max(0, cur.rowcount)
    return counts


async def retention_worker() -> None:
    await asyncio.sleep(60)
    while True:
        try:
            cleanup_once()
        except Exception:
            pass
        await asyncio.sleep(24 * 60 * 60)


def install(app) -> None:
    @app.on_event("startup")
    async def _start_retention_worker():
        cleanup_once()
        asyncio.create_task(retention_worker())
