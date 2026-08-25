from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header, Query

from . import auth, storage
from .conscious_mind import mind
from .topology import FRONT_CORE

router = APIRouter()


@router.get("/desktop/stream-observe")
def stream_observe(limit: int = Query(default=160, ge=1, le=400), authorization: Optional[str] = Header(default=None)):
    account = auth.require_account(authorization)
    aid = int(account["id"])
    runtime = mind.status(aid)
    items = storage.rows(
        "SELECT id,core_name,event_type,mode,public_detail AS detail,created_at FROM v2_events "
        "WHERE account_id=? AND core_name IN ('front','consensus') ORDER BY id DESC LIMIT ?",
        (aid, int(limit)),
    )
    front = (runtime.get("cores") or {}).get(FRONT_CORE, {})
    nested = front.get("recursive_janus") or {}
    return {
        "profile": account["username"],
        "core": FRONT_CORE,
        "stream_of_consciousness": True,
        "externalizable_only": True,
        "phase": runtime.get("phase"),
        "rest_is_passive": runtime.get("rest_is_passive", True),
        "foreground_can_rouse": runtime.get("foreground_can_rouse", True),
        "last_rouse_at": runtime.get("last_rouse_at", 0),
        "current": {
            "summary": front.get("summary", ""),
            "appraisal": front.get("appraisal", {}),
            "recursive_janus": nested,
        },
        "items": items,
    }
