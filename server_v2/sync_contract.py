from __future__ import annotations

from typing import Any, Optional
from fastapi import APIRouter, Header

from . import auth
from .mind import mind

router = APIRouter()


@router.post("/core-sync/exchange")
def exchange(payload: dict[str, Any], authorization: Optional[str] = Header(default=None)):
    account = auth.require_account(authorization)
    result = mind.ingest_device(int(account["id"]), payload)
    status = mind.status(int(account["id"]))
    cores = status.get("cores") or {}
    # This exact `server` envelope is the clean federation contract consumed by
    # the native client. Remote material is feedback-only on the device and is
    # reintroduced through specialist review there; it never overwrites local state.
    result["server"] = {
        "phase": status.get("phase"),
        "core_count": status.get("core_count"),
        "consensus": str((cores.get("consensus") or {}).get("summary") or ""),
        "interface": str((cores.get("interface") or {}).get("summary") or ""),
        "architecture": "7->2->1->1",
        "sync_policy": "selective-no-overwrite",
    }
    return result
