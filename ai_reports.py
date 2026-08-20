"""In-app reporting and moderation queue for JANUS AI responses."""
from __future__ import annotations

import os
import sqlite3
import time
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, field_validator

import auth

router = APIRouter(tags=["ai-safety"])
DB_PATH = os.getenv("JANUS_DB_PATH", "/data/janus.sqlite3")
CATEGORIES = {"harmful", "harassment", "sexual", "hate", "self-harm", "illegal", "privacy", "misinformation", "other"}


def _db():
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    return c


def init_reports():
    with _db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS ai_response_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_account_id INTEGER,
            reporter_username TEXT,
            category TEXT NOT NULL,
            response_text TEXT NOT NULL,
            user_context TEXT,
            details TEXT,
            created_at INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            resolution_note TEXT,
            reviewed_at INTEGER
        )""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_ai_reports_status ON ai_response_reports(status,created_at)")


def _bearer(authorization: Optional[str]):
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    return authorization.split(" ", 1)[1].strip()


def _require_account(authorization: Optional[str]):
    account = auth.account_for_token(_bearer(authorization))
    if not account:
        raise HTTPException(401, "Valid JANUS session required")
    return account


def _require_admin(token: Optional[str]):
    expected = os.getenv("JANUS_ACCESS_TOKEN", "")
    if not expected or not token or token != expected:
        raise HTTPException(403, "Admin access required")


class ReportRequest(BaseModel):
    category: str
    response_text: str
    user_context: Optional[str] = None
    details: Optional[str] = None

    @field_validator("category")
    @classmethod
    def valid_category(cls, value: str):
        value = value.strip().lower()
        if value not in CATEGORIES:
            raise ValueError("invalid report category")
        return value

    @field_validator("response_text")
    @classmethod
    def valid_response(cls, value: str):
        value = value.strip()
        if not value:
            raise ValueError("response text is required")
        return value[:12000]


class ReviewRequest(BaseModel):
    status: str
    resolution_note: Optional[str] = None

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: str):
        value = value.strip().lower()
        if value not in {"open", "reviewing", "resolved", "dismissed"}:
            raise ValueError("invalid status")
        return value


@router.post("/safety/report")
def report_ai_response(req: ReportRequest, authorization: Optional[str] = Header(default=None)):
    account = _require_account(authorization)
    init_reports()
    now = int(time.time())
    with _db() as c:
        cur = c.execute(
            """INSERT INTO ai_response_reports(
                reporter_account_id,reporter_username,category,response_text,user_context,details,created_at
            ) VALUES(?,?,?,?,?,?,?)""",
            (
                int(account["id"]), str(account["username"]), req.category,
                req.response_text, (req.user_context or "")[:4000], (req.details or "")[:2000], now,
            ),
        )
        report_id = int(cur.lastrowid)
    return {"ok": True, "report_id": report_id, "message": "Report submitted for review."}


@router.get("/admin/safety/reports")
def list_reports(
    status: str = Query(default="open"),
    limit: int = Query(default=100, ge=1, le=500),
    x_janus_admin_token: Optional[str] = Header(default=None),
):
    _require_admin(x_janus_admin_token)
    init_reports()
    with _db() as c:
        rows = c.execute(
            "SELECT * FROM ai_response_reports WHERE status=? ORDER BY created_at DESC LIMIT ?",
            (status, limit),
        ).fetchall()
    return {"items": [dict(r) for r in rows]}


@router.patch("/admin/safety/reports/{report_id}")
def review_report(
    report_id: int,
    req: ReviewRequest,
    x_janus_admin_token: Optional[str] = Header(default=None),
):
    _require_admin(x_janus_admin_token)
    init_reports()
    with _db() as c:
        cur = c.execute(
            "UPDATE ai_response_reports SET status=?,resolution_note=?,reviewed_at=? WHERE id=?",
            (req.status, (req.resolution_note or "")[:4000], int(time.time()), report_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(404, "Report not found")
    return {"ok": True, "report_id": report_id, "status": req.status}


init_reports()
