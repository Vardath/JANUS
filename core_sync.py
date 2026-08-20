"""Authenticated compact synchronization between JANUS client and global 11-core runtimes."""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

import auth
from src.janus_sleep_cycle import janus_sleep_cycle

router = APIRouter(prefix="/core-sync", tags=["core-sync"])

class CoreSummary(BaseModel):
    device_id: str = Field(min_length=1, max_length=128)
    phase: str = Field(default="unknown", max_length=32)
    consensus: str = Field(default="", max_length=1000)
    interface: str = Field(default="", max_length=1000)
    cycles: dict[str, int] = Field(default_factory=dict)


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
    device_key = f"acct-{account['id']}:{summary.device_id}"
    janus_sleep_cycle.accept_remote_summary(device_key, summary.model_dump())
    return {
        "ok": True,
        "server": janus_sleep_cycle.compact_summary(),
        "account_id": int(account["id"]),
    }


@router.get("/status")
def status(authorization: Optional[str] = Header(default=None)):
    _require(authorization)
    return janus_sleep_cycle.status()
