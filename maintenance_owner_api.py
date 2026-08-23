"""Authenticated owner-facing maintenance review API.

This module exposes JANUS's existing quarterly maintenance proposals to the configured
owner account. Decisions are advisory state only: approve/defer/reject never execute
code changes, dependency upgrades, model switches, configuration changes or deploys.
"""
from __future__ import annotations

import json
import os
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

import auth
import maintenance_review

router = APIRouter(prefix="/maintenance", tags=["maintenance"])


class DecisionRequest(BaseModel):
    decision: str


def _owner_account(authorization: Optional[str]):
    account = auth.require_account(authorization)
    if not account:
        raise HTTPException(401, "authentication required")
    configured = os.getenv("JANUS_MAINTENANCE_OWNER_PROFILE", "").strip()
    username = str(account.get("username") or "").strip()
    if not configured:
        raise HTTPException(503, "maintenance owner profile is not configured")
    if username != configured:
        raise HTTPException(403, "maintenance review is restricted to the configured owner")
    return account


def _decode_review(row: dict | None) -> dict | None:
    if not row:
        return None
    out = dict(row)
    raw = out.pop("report_json", "") or ""
    try:
        out["report"] = json.loads(raw) if raw else {}
    except Exception:
        out["report"] = {}
    # Keep the owner UI useful without exposing mail transport internals.
    out.pop("email_body", None)
    out.pop("notification_error", None)
    return out


def _list_reviews(limit: int = 12) -> list[dict]:
    maintenance_review._init_db()
    with maintenance_review._db() as c:
        rows = c.execute(
            "SELECT * FROM janus_maintenance_review ORDER BY id DESC LIMIT ?",
            (max(1, min(50, int(limit))),),
        ).fetchall()
    return [_decode_review(dict(r)) for r in rows]


@router.get("/status")
def owner_status(authorization: Optional[str] = Header(default=None)):
    _owner_account(authorization)
    state = maintenance_review.status()
    reviews = _list_reviews()
    state["last_review"] = _decode_review(state.get("last_review"))
    return {
        "ok": True,
        "maintenance": state,
        "reviews": reviews,
        "allowed_decisions": ["approved_for_manual_work", "deferred", "rejected"],
        "automatic_changes": False,
        "owner_approval_required": True,
    }


@router.post("/reviews/{review_id}/decision")
def decide(review_id: int, req: DecisionRequest, authorization: Optional[str] = Header(default=None)):
    _owner_account(authorization)
    decision = str(req.decision or "").strip().lower()
    if decision not in {"approved_for_manual_work", "deferred", "rejected"}:
        raise HTTPException(400, "decision must be approved_for_manual_work, deferred, or rejected")
    try:
        result = maintenance_review.acknowledge(review_id, decision)
    except KeyError:
        raise HTTPException(404, "maintenance review not found")
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    result.update({
        "ok": True,
        "manual_work_only": decision == "approved_for_manual_work",
        "automatic_changes": False,
        "message": (
            "Approved for manual review/work only; JANUS has not changed code or deployed anything."
            if decision == "approved_for_manual_work" else
            "Maintenance review deferred; no changes were made."
            if decision == "deferred" else
            "Maintenance review rejected; no changes were made."
        ),
    })
    return result
