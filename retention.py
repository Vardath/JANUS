"""JANUS retention policy enforcement.

User conversation/memory content is retained until account deletion because
continuity is a core feature. Security, idempotency and low-value telemetry have
shorter retention so multi-device/background testing cannot grow the disk without
bound.
"""
from __future__ import annotations

import asyncio
import os
import time
from datetime import datetime, timezone, timedelta

import auth

AUTH_TOKEN_CLEANUP_DAYS = max(1, int(os.getenv("JANUS_AUTH_TOKEN_CLEANUP_DAYS", "7")))
DELETION_REQUEST_RETENTION_DAYS = max(1, int(os.getenv("JANUS_DELETION_REQUEST_RETENTION_DAYS", "90")))
CHAT_RECEIPT_RETENTION_DAYS = max(1, int(os.getenv("JANUS_CHAT_RECEIPT_RETENTION_DAYS", "7")))
RUNTIME_SNAPSHOT_RETENTION_DAYS = max(1, int(os.getenv("JANUS_RUNTIME_SNAPSHOT_RETENTION_DAYS", "30")))


def _table_exists(c, name: str) -> bool:
    return bool(c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone())


def cleanup_once() -> dict[str, int]:
    now = int(time.time())
    token_cutoff = now - AUTH_TOKEN_CLEANUP_DAYS * 86400
    deletion_cutoff = now - DELETION_REQUEST_RETENTION_DAYS * 86400
    receipt_cutoff = now - CHAT_RECEIPT_RETENTION_DAYS * 86400
    snapshot_cutoff = (datetime.now(timezone.utc) - timedelta(days=RUNTIME_SNAPSHOT_RETENTION_DAYS)).isoformat()
    counts = {
        "sessions": 0,
        "auth_tokens": 0,
        "deletion_requests": 0,
        "chat_receipts": 0,
        "runtime_snapshots": 0,
        "profile_ingest_claims": 0,
    }
    with auth._db() as c:
        cur = c.execute("DELETE FROM sessions WHERE expires_at<=?", (now,))
        counts["sessions"] = max(0, cur.rowcount)
        cur = c.execute(
            "DELETE FROM auth_tokens WHERE expires_at<=? OR (used_at IS NOT NULL AND used_at<=?)",
            (now, token_cutoff),
        )
        counts["auth_tokens"] = max(0, cur.rowcount)

        if _table_exists(c, "account_deletion_requests"):
            cur = c.execute(
                "DELETE FROM account_deletion_requests WHERE requested_at<=? AND status='pending'",
                (deletion_cutoff,),
            )
            counts["deletion_requests"] = max(0, cur.rowcount)

        if _table_exists(c, "janus_chat_receipts"):
            cur = c.execute("DELETE FROM janus_chat_receipts WHERE updated_at<=?", (receipt_cutoff,))
            counts["chat_receipts"] = max(0, cur.rowcount)

        # Detailed user-visible conversation and memory are retained. Only the
        # repetitive cycle-counter snapshots are bounded here.
        if _table_exists(c, "desktop_events"):
            cur = c.execute(
                "DELETE FROM desktop_events WHERE event_type='core_runtime_snapshot' AND created_at<=?",
                (snapshot_cutoff,),
            )
            counts["runtime_snapshots"] = max(0, cur.rowcount)

        # Ingest claims only exist to suppress duplicate device events. Once the
        # matching low-value runtime snapshot window has passed they need not live
        # forever; event/message content itself is unaffected.
        if _table_exists(c, "janus_core_profile_ingest"):
            cur = c.execute(
                "DELETE FROM janus_core_profile_ingest WHERE source_event_id LIKE 'snapshot:%' AND created_at<=?",
                (snapshot_cutoff,),
            )
            counts["profile_ingest_claims"] = max(0, cur.rowcount)
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
