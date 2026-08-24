from __future__ import annotations

import os
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException

from . import auth, storage

router = APIRouter()


def _owner_account():
    configured=os.getenv("JANUS_MAINTENANCE_OWNER_PROFILE","").strip()
    if configured:
        return storage.account_by_identifier(configured), "configured-profile"
    row=storage.one("SELECT * FROM v2_accounts ORDER BY id ASC LIMIT 1")
    return row, "first-account-fallback"


def _require_owner(authorization: Optional[str]):
    account=auth.require_account(authorization)
    owner,basis=_owner_account()
    if owner is None or int(account["id"]) != int(owner["id"]):
        raise HTTPException(403,"Maintenance decisions are restricted to the JANUS owner account")
    return account,basis


@router.get("/maintenance/status")
def status(authorization: Optional[str]=Header(default=None)):
    account=auth.require_account(authorization); aid=int(account["id"])
    owner,basis=_owner_account(); is_owner=bool(owner and int(owner["id"])==aid)
    reviews=storage.rows("SELECT id,report_json,review_state,created_at,decided_at FROM v2_maintenance WHERE account_id=? ORDER BY id DESC LIMIT 30",(aid,))
    for item in reviews: item["report"]=storage.jload(item.pop("report_json"),{})
    return {
        "ok":True,
        "maintenance":{"enabled":True,"interval_days":90,"due":False,"automatic_code_changes":False,"automatic_deploy":False,"owner_gated":True},
        "is_owner":is_owner,"owner_resolution":basis if is_owner else "restricted","reviews":reviews,
    }


@router.post("/maintenance/reviews/{review_id}/decision")
def decision(review_id:int,payload:dict[str,Any],authorization:Optional[str]=Header(default=None)):
    account,basis=_require_owner(authorization); aid=int(account["id"])
    value=str(payload.get("decision") or "")
    if value not in {"approved_for_manual_work","deferred","rejected"}: raise HTTPException(400,"invalid decision")
    with storage.db() as c:
        found=c.execute("SELECT 1 FROM v2_maintenance WHERE id=? AND account_id=?",(review_id,aid)).fetchone()
        if not found: raise HTTPException(404,"maintenance review not found")
        c.execute("UPDATE v2_maintenance SET review_state=?,decided_at=? WHERE id=?",(value,storage.now(),review_id))
    return {"ok":True,"review_id":review_id,"decision":value,"automatic_changes":False,"automatic_deploy":False,"owner_resolution":basis}
