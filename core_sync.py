"""Authenticated compact synchronization and presence for JANUS local/global runtimes."""
from __future__ import annotations

import json
import os
import sqlite3
import time
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

import auth
from src.janus_sleep_cycle import janus_sleep_cycle
from core_observer import ingest_remote_events, record_remote_snapshot
from core_activity_bridge import ingest_profile_core_activity
from deliberation_sync import active_for_profile

router = APIRouter(prefix="/core-sync", tags=["core-sync"])
DB_PATH = os.environ.get("JANUS_DB_PATH", "/data/janus.sqlite3")
PRESENCE_TTL_SECONDS = max(30, int(os.environ.get("JANUS_CLIENT_PRESENCE_TTL_SECONDS", "90")))
MAX_SHARED_ITEMS = max(1, min(24, int(os.environ.get("JANUS_SYNC_MAX_SHARED_ITEMS", "8"))))


class CoreSummary(BaseModel):
    device_id: str = Field(min_length=1, max_length=128)
    platform: str = Field(default="unknown", max_length=32)
    client_version: str = Field(default="unknown", max_length=32)
    phase: str = Field(default="unknown", max_length=32)
    consensus: str = Field(default="", max_length=1000)
    interface: str = Field(default="", max_length=1000)
    cycles: dict[str, int] = Field(default_factory=dict)
    observe_events: list[dict] = Field(default_factory=list, max_length=100)
    memories: list[str] = Field(default_factory=list, max_length=24)
    conclusions: list[str] = Field(default_factory=list, max_length=24)


def _db():
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute(
        """CREATE TABLE IF NOT EXISTS janus_client_presence(
        account_id INTEGER NOT NULL,
        profile_id TEXT NOT NULL,
        device_id TEXT NOT NULL,
        platform TEXT NOT NULL DEFAULT 'unknown',
        client_version TEXT NOT NULL DEFAULT 'unknown',
        phase TEXT NOT NULL DEFAULT 'unknown',
        cycles_json TEXT NOT NULL DEFAULT '{}',
        last_seen_at INTEGER NOT NULL,
        last_sync_ok INTEGER NOT NULL DEFAULT 1,
        last_sync_error TEXT NOT NULL DEFAULT '',
        PRIMARY KEY(account_id,device_id)
        )"""
    )
    return c


def _bearer(authorization: Optional[str]):
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    return authorization.split(" ", 1)[1].strip()


def _require(authorization: Optional[str]):
    account = auth.account_for_token(_bearer(authorization))
    if not account:
        raise HTTPException(401, "Valid JANUS session required")
    return account


def _account_value(account, key: str, default=None):
    try:
        value = account[key]
    except Exception:
        try:
            value = account.get(key, default)
        except Exception:
            value = default
    return default if value is None else value


def _identity(account):
    account_id = int(_account_value(account, "id", 0) or 0)
    if account_id <= 0:
        raise HTTPException(401, "Authenticated account has no valid id")
    username = str(_account_value(account, "username", "") or "").strip()
    email = str(_account_value(account, "email", "") or "").strip()
    return account_id, username or email or f"acct-{account_id}"


def _safe_count(callable_, label: str, errors: list[str]) -> int:
    try:
        return int(callable_() or 0)
    except Exception as exc:
        errors.append(f"{label}: {type(exc).__name__}: {str(exc)[:240]}")
        return 0


def _safe_profile_records(callable_, errors: list[str]) -> dict:
    try:
        result = callable_() or {}
        return result if isinstance(result, dict) else {}
    except Exception as exc:
        errors.append(f"profile-persistence: {type(exc).__name__}: {str(exc)[:240]}")
        return {}


def _record_presence(account_id: int, profile_id: str, summary: CoreSummary, errors: list[str]):
    now = int(time.time())
    try:
        with _db() as c:
            c.execute(
                """INSERT INTO janus_client_presence(account_id,profile_id,device_id,platform,client_version,phase,cycles_json,last_seen_at,last_sync_ok,last_sync_error)
                VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(account_id,device_id) DO UPDATE SET
                profile_id=excluded.profile_id,platform=excluded.platform,client_version=excluded.client_version,
                phase=excluded.phase,cycles_json=excluded.cycles_json,last_seen_at=excluded.last_seen_at,
                last_sync_ok=excluded.last_sync_ok,last_sync_error=excluded.last_sync_error""",
                (account_id, profile_id, summary.device_id, summary.platform, summary.client_version,
                 summary.phase, json.dumps(summary.cycles, separators=(",", ":")), now, 0 if errors else 1,
                 " | ".join(errors)[:1000]),
            )
    except Exception as exc:
        errors.append(f"presence-persistence: {type(exc).__name__}: {str(exc)[:240]}")


def _decode_presence_rows(rows):
    now = int(time.time())
    items = []
    for row in rows:
        age = max(0, now - int(row["last_seen_at"] or 0))
        try:
            cycles = json.loads(row["cycles_json"] or "{}")
        except Exception:
            cycles = {}
        items.append({
            "device_id": row["device_id"], "platform": row["platform"], "client_version": row["client_version"],
            "phase": row["phase"], "cycles": cycles, "last_seen_at": int(row["last_seen_at"] or 0),
            "age_seconds": age, "online": age <= PRESENCE_TTL_SECONDS,
            "last_sync_ok": bool(row["last_sync_ok"]), "last_sync_error": row["last_sync_error"],
        })
    return items


def _presence(account_id: int):
    with _db() as c:
        rows = c.execute(
            "SELECT device_id,platform,client_version,phase,cycles_json,last_seen_at,last_sync_ok,last_sync_error FROM janus_client_presence WHERE account_id=? ORDER BY last_seen_at DESC",
            (account_id,),
        ).fetchall()
    return _decode_presence_rows(rows)


def presence_for_profile(profile_id: str):
    """Return presence rows for the authenticated profile selected by secure desktop routes."""
    profile = str(profile_id or "").strip()
    if not profile:
        return []
    with _db() as c:
        rows = c.execute(
            "SELECT device_id,platform,client_version,phase,cycles_json,last_seen_at,last_sync_ok,last_sync_error FROM janus_client_presence WHERE profile_id=? ORDER BY last_seen_at DESC",
            (profile,),
        ).fetchall()
    return _decode_presence_rows(rows)


def _shared_state(profile_id: str):
    """Return bounded, tagged global material only; never local queue/cycle/device identity state."""
    active = active_for_profile(profile_id)
    runtime = janus_sleep_cycle.compact_summary()
    items = []
    for label, value in (("global_consensus", runtime.get("consensus")), ("global_interface", runtime.get("interface"))):
        text = str(value or "").strip()
        if text:
            items.append({"kind": label, "text": text[:1200], "provenance": "global_janus"})
    if active:
        text = str(active.get("current_summary") or active.get("topic") or "").strip()
        if text:
            items.append({"kind": "deliberation_progress", "text": text[:1200], "provenance": "global_janus"})
    return {"items": items[:MAX_SHARED_ITEMS], "policy": "tagged_grounding_only"}


@router.post("/exchange")
def exchange(summary: CoreSummary, authorization: Optional[str] = Header(default=None)):
    account = _require(authorization)
    account_id, profile_id = _identity(account)
    device_key = f"acct-{account_id}:{summary.device_id}"
    data = summary.model_dump()
    errors: list[str] = []

    try:
        janus_sleep_cycle.accept_remote_summary(device_key, data)
    except Exception as exc:
        errors.append(f"runtime-intake: {type(exc).__name__}: {str(exc)[:240]}")

    observed = _safe_count(lambda: ingest_remote_events(device_key, data.get("observe_events") or [], profile_id=profile_id), "observe-persistence", errors)
    snapshots = _safe_count(lambda: record_remote_snapshot(device_key, data, profile_id=profile_id), "snapshot-persistence", errors)
    profile_records = _safe_profile_records(lambda: ingest_profile_core_activity(profile_id, device_key, data), errors)

    remote_notes = [str(x).strip()[:1200] for x in (summary.memories + summary.conclusions) if str(x).strip()][:MAX_SHARED_ITEMS]
    for text in remote_notes:
        for target in ("evidence", "context", "memory", "safety"):
            janus_sleep_cycle.send("interface", target, f"remote-grounding [{summary.device_id}]: {text}", "remote_grounding")
    if remote_notes:
        janus_sleep_cycle.service_work_burst(include_interface=True, only_if_pending=True)

    _record_presence(account_id, profile_id, summary, errors)
    presence = _presence(account_id)

    # Return the full authoritative server runtime on the heartbeat itself. Android
    # already performs this authenticated exchange every 15 seconds, so the UI can
    # display exactly the same server society without a second WebView HTTP path.
    server_summary = janus_sleep_cycle.status()
    server_summary["remote_clients"] = sum(1 for x in presence if x["online"])
    server_summary["registered_clients"] = len(presence)
    active_deliberation = active_for_profile(profile_id)

    return {
        "ok": True, "server": server_summary, "shared_state": _shared_state(profile_id),
        "active_deliberation": active_deliberation,
        "presence": {"online": sum(1 for x in presence if x["online"]), "registered": len(presence), "clients": presence[:20]},
        "account_id": account_id, "profile_id": profile_id,
        "observed_events_received": observed, "runtime_snapshots_recorded": snapshots,
        "profile_activity_recorded": int(profile_records.get("activity", 0) or 0),
        "profile_memory_recorded": int(profile_records.get("memory", 0) or 0),
        "profile_messages_recorded": int(profile_records.get("messages", 0) or 0),
        "profile_snapshots_recorded": int(profile_records.get("snapshots", 0) or 0),
        "sync_degraded": bool(errors), "sync_errors": errors,
    }


@router.get("/status")
def status(authorization: Optional[str] = Header(default=None)):
    account = _require(authorization)
    account_id, profile_id = _identity(account)
    presence = _presence(account_id)
    runtime = janus_sleep_cycle.status()
    runtime["remote_clients"] = sum(1 for x in presence if x["online"])
    runtime["registered_clients"] = len(presence)
    runtime["clients"] = presence[:50]
    runtime["profile_id"] = profile_id
    return runtime
