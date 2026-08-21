"""Authenticated compact synchronization between JANUS client and global 11-core runtimes."""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

import auth
from src.janus_sleep_cycle import janus_sleep_cycle
from core_observer import ingest_remote_events, record_remote_snapshot

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


@router.post("/exchange")
def exchange(summary: CoreSummary, authorization: Optional[str] = Header(default=None)):
    account = _require(authorization)
    profile_id=str(account.get("username") or account.get("email") or f"acct-{account['id']}")
    device_key = f"acct-{account['id']}:{summary.device_id}"
    data=summary.model_dump()
    janus_sleep_cycle.accept_remote_summary(device_key, data)
    observed=ingest_remote_events(device_key, data.get("observe_events") or [], profile_id=profile_id)
    snapshots=record_remote_snapshot(device_key, data, profile_id=profile_id)
    return {
        "ok": True,
        "server": janus_sleep_cycle.compact_summary(),
        "account_id": int(account["id"]),
        "observed_events_received": observed,
        "runtime_snapshots_recorded": snapshots,
    }


@router.get("/status")
def status(authorization: Optional[str] = Header(default=None)):
    _require(authorization)
    return janus_sleep_cycle.status()
