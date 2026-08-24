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
    front = cores.get("front") or cores.get("consensus") or {}
    interface = cores.get("interface") or {}

    # Clients receive only bounded externalizable state. The peer snapshot must
    # re-enter the receiving society through all seven sensory projections; it has
    # no authority to overwrite the receiving Front, Interface or protected state.
    front_summary = str(front.get("summary") or "")
    result["server"] = {
        "phase": status.get("phase"),
        "core_count": status.get("core_count"),
        "front": front_summary,
        "front_appraisal": front.get("appraisal") or {},
        "consensus": front_summary,  # temporary compatibility alias
        "interface": str(interface.get("summary") or ""),
        "interface_appraisal": interface.get("appraisal") or {},
        "architecture": status.get("architecture"),
        "conceptual_topology": status.get("conceptual_topology", "1|3|7"),
        "mechanical_flow": status.get("mechanical_flow", "7 -> 2 -> 1 -> 1"),
        "sync_policy": "selective-no-overwrite",
        "peer_policy": "reenter-through-all-seven-senses",
    }
    result["presence"] = {
        "online": int(status.get("remote_clients") or 0),
        "registered": int(status.get("registered_clients") or 0),
        "clients": status.get("clients") or [],
    }
    return result
