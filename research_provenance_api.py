"""Authenticated account-scoped background research provenance summary."""
from __future__ import annotations

import json
from typing import Optional
from fastapi import APIRouter, Header

import auth
import background_usefulness
import cost_governor
import curiosity_search

router = APIRouter(prefix="/research-provenance", tags=["research-provenance"])


def _recent_searches(profile: str, limit: int = 20) -> list[dict]:
    limit = max(1, min(int(limit or 20), 50))
    try:
        with curiosity_search._db() as c:
            rows = c.execute(
                "SELECT id,core_name,mode,query,rationale,result,sources_json,status,created_at,completed_at "
                "FROM janus_curiosity_searches WHERE profile_id=? ORDER BY id DESC LIMIT ?",
                (profile, limit),
            ).fetchall()
    except Exception:
        return []
    out = []
    for row in rows:
        item = dict(row)
        try:
            item["sources"] = json.loads(item.pop("sources_json") or "[]")
        except Exception:
            item["sources"] = []
            item.pop("sources_json", None)
        item["source_count"] = len(item["sources"])
        item["result_preview"] = " ".join(str(item.pop("result", "") or "").split())[:900]
        out.append(item)
    return out


@router.get("/status")
def provenance_status(limit: int = 20, authorization: Optional[str] = Header(default=None)):
    account = auth.require_account(authorization)
    profile = str(account["username"])
    usefulness = background_usefulness.audit(profile, max(limit, 30))
    cost = cost_governor.status(profile)
    searches = _recent_searches(profile, limit)
    return {
        "ok": True,
        "profile": profile,
        "recent_searches": searches,
        "usefulness": usefulness,
        "external_compute": cost,
        "provenance_notice": "Sources and costs describe externalized research activity only; they are not private chain-of-thought or provider billing statements.",
        "background_image_generation_enabled": False,
    }
