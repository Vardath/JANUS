"""Authenticated compact synchronization between JANUS client and global 11-core runtimes."""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

import auth
from src.janus_sleep_cycle import janus_sleep_cycle
from core_observer import ingest_remote_events, record_remote_snapshot
from core_activity_bridge import ingest_profile_core_activity
from deliberation_sync import active_for_profile

router = APIRouter(prefix="/core-sync", tags=["core-sync"])

class CoreSummary(BaseModel):
    device_id: str = Field(min_length=1, max_length=128)
    phase: str = Field(default="unknown", max_length=32)
    consensus: str = Field(default="", max_length=1000)
    interface: str = Field(default="", max_length=1000)
    cycles: dict[str, int] = Field(default_factory=dict)
    observe_events: list[dict] = Field(default_factory=list, max_length=100)


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
    """Read either sqlite3.Row or dict-like account records safely."""
    try:
        value = account[key]
    except Exception:
        try:
            value = account.get(key, default)
        except Exception:
            value = default
    return default if value is None else value


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


@router.post("/exchange")
def exchange(summary: CoreSummary, authorization: Optional[str] = Header(default=None)):
    account = _require(authorization)
    account_id = int(_account_value(account, "id", 0) or 0)
    if account_id <= 0:
        raise HTTPException(401, "Authenticated account has no valid id")
    username = str(_account_value(account, "username", "") or "").strip()
    email = str(_account_value(account, "email", "") or "").strip()
    profile_id = username or email or f"acct-{account_id}"
    device_key = f"acct-{account_id}:{summary.device_id}"
    data = summary.model_dump()

    errors: list[str] = []
    try:
        janus_sleep_cycle.accept_remote_summary(device_key, data)
    except Exception as exc:
        errors.append(f"runtime-intake: {type(exc).__name__}: {str(exc)[:240]}")

    observed = _safe_count(
        lambda: ingest_remote_events(device_key, data.get("observe_events") or [], profile_id=profile_id),
        "observe-persistence",
        errors,
    )
    snapshots = _safe_count(
        lambda: record_remote_snapshot(device_key, data, profile_id=profile_id),
        "snapshot-persistence",
        errors,
    )
    profile_records = _safe_profile_records(
        lambda: ingest_profile_core_activity(profile_id, device_key, data),
        errors,
    )

    try:
        server_summary = janus_sleep_cycle.compact_summary()
    except Exception as exc:
        errors.append(f"server-summary: {type(exc).__name__}: {str(exc)[:240]}")
        server_summary = {"architecture": "11 Fano/JANUS cores", "topology": "7 -> 2 -> 1 -> 1", "interface_available": True}

    active_deliberation = active_for_profile(profile_id)

    return {
        "ok": True,
        "server": server_summary,
        "active_deliberation": active_deliberation,
        "account_id": account_id,
        "profile_id": profile_id,
        "observed_events_received": observed,
        "runtime_snapshots_recorded": snapshots,
        "profile_activity_recorded": int(profile_records.get("activity", 0) or 0),
        "profile_memory_recorded": int(profile_records.get("memory", 0) or 0),
        "profile_messages_recorded": int(profile_records.get("messages", 0) or 0),
        "profile_snapshots_recorded": int(profile_records.get("snapshots", 0) or 0),
        "sync_degraded": bool(errors),
        "sync_errors": errors,
    }


@router.get("/status")
def status(authorization: Optional[str] = Header(default=None)):
    _require(authorization)
    return janus_sleep_cycle.status()
