"""Account deletion flows for JANUS.

Provides:
- authenticated in-app deletion that removes the account and known user-scoped data;
- a public web page and request form suitable for a Google Play deletion URL.
"""
from __future__ import annotations

import html
import os
import sqlite3
import time
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr

import auth

router = APIRouter(tags=["account-deletion"])
DB_PATH = os.environ.get("JANUS_DB_PATH", "/data/janus.sqlite3")


class DeleteAccountRequest(BaseModel):
    confirmation: str
    current_password: Optional[str] = None


class PublicDeletionRequest(BaseModel):
    email: EmailStr


def _bearer(authorization: Optional[str]) -> Optional[str]:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    return authorization.split(" ", 1)[1].strip()


def _require_account(authorization: Optional[str]):
    token = _bearer(authorization)
    account = auth.account_for_token(token)
    if not account:
        raise HTTPException(401, "Valid JANUS session required")
    return token, account


def _app_db():
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    return c


def _delete_profile_data(profile: str) -> dict[str, int]:
    """Delete known JANUS data partitioned by profile_id."""
    deleted: dict[str, int] = {}
    c = _app_db()
    try:
        for table in (
            "janus_message_state",
            "janus_reflection_promotion",
            "desktop_events",
            "desktop_memory",
        ):
            exists = c.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
            ).fetchone()
            if not exists:
                continue
            cur = c.execute(f"DELETE FROM {table} WHERE profile_id=?", (profile,))
            deleted[table] = max(0, cur.rowcount)
        c.commit()
    finally:
        c.close()
    return deleted


def _delete_attachment_audit(account_id: int) -> int:
    c = _app_db()
    try:
        exists = c.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='janus_file_audit_log'"
        ).fetchone()
        if not exists:
            return 0
        cur = c.execute("DELETE FROM janus_file_audit_log WHERE account_id=?", (int(account_id),))
        c.commit()
        return max(0, cur.rowcount)
    finally:
        c.close()


def _delete_client_presence(account_id: int) -> int:
    c = _app_db()
    try:
        exists = c.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='janus_client_presence'"
        ).fetchone()
        if not exists:
            return 0
        cur = c.execute("DELETE FROM janus_client_presence WHERE account_id=?", (int(account_id),))
        c.commit()
        return max(0, cur.rowcount)
    finally:
        c.close()


def _delete_visual_cache(account_id: int) -> int:
    try:
        from vision_analysis import cleanup_account
        return int(cleanup_account(int(account_id)) or 0)
    except Exception:
        return 0


def _ensure_public_request_table():
    with auth._db() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS account_deletion_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL COLLATE NOCASE,
                requested_at INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending'
            )"""
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_deletion_requests_email ON account_deletion_requests(email,status)"
        )


@router.delete("/auth/account")
def delete_account(req: DeleteAccountRequest, authorization: Optional[str] = Header(default=None)):
    token, account = _require_account(authorization)
    if req.confirmation.strip().upper() != "DELETE":
        raise HTTPException(400, "Type DELETE to confirm permanent account deletion")

    account_id = int(account["id"])
    username = str(account["username"])

    with auth._db() as c:
        row = c.execute(
            "SELECT password_hash FROM accounts WHERE id=?", (account_id,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "Account not found")
        password_hash = str(row["password_hash"])
        if password_hash != "google_only":
            if not req.current_password or not auth._verify_password(req.current_password, password_hash):
                raise HTTPException(401, "Current password is required to delete this account")

    removed = _delete_profile_data(username)
    attachment_files_deleted = 0
    try:
        from attachment_api import cleanup_account_files
        attachment_files_deleted = cleanup_account_files(account_id)
    except Exception:
        attachment_files_deleted = 0
    attachment_audit_rows_deleted = _delete_attachment_audit(account_id)
    client_presence_rows_deleted = _delete_client_presence(account_id)
    visual_cache_rows_deleted = _delete_visual_cache(account_id)

    with auth._db() as c:
        c.execute("DELETE FROM account_deletion_requests WHERE email=? COLLATE NOCASE", (account["email"],))
        c.execute("DELETE FROM accounts WHERE id=?", (account_id,))

    return {
        "ok": True,
        "deleted": True,
        "message": "JANUS account and known associated user data were deleted.",
        "profile_rows_deleted": removed,
        "attachment_files_deleted": attachment_files_deleted,
        "attachment_audit_rows_deleted": attachment_audit_rows_deleted,
        "client_presence_rows_deleted": client_presence_rows_deleted,
        "visual_cache_rows_deleted": visual_cache_rows_deleted,
    }


@router.get("/delete-account", response_class=HTMLResponse)
def delete_account_page():
    return HTMLResponse(
        """<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
        <title>Delete JANUS account</title><style>body{font-family:Arial,sans-serif;max-width:720px;margin:40px auto;padding:0 18px;line-height:1.5}input,button{font:inherit;padding:10px;margin:6px 0;width:100%;box-sizing:border-box}button{background:#111;color:#fff;border:0;border-radius:8px}small{color:#666}</style></head><body>
        <h1>Delete your JANUS account</h1>
        <p>You can permanently delete your JANUS account from inside the JANUS Android app. This removes the account, active sessions, authentication tokens, known JANUS conversation, memory, activity, message data, uploaded files, file-retention audit history, cached visual assessments and registered device-presence history associated with the account.</p>
        <p>If you cannot access the app, submit the email address used for your JANUS account below. This creates an account-deletion request for identity verification and processing.</p>
        <form id='f'><input id='email' type='email' required placeholder='JANUS account email'><button>Request account deletion</button></form>
        <p id='result'></p><small>For security, a public request does not immediately delete an account merely because someone knows its email address.</small>
        <script>document.getElementById('f').addEventListener('submit',async(e)=>{e.preventDefault();let r=document.getElementById('result');r.textContent='Submitting…';try{let x=await fetch('/account-deletion/request',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:document.getElementById('email').value})});let j=await x.json();r.textContent=j.message||'Request received.'}catch(err){r.textContent='Unable to submit the request right now.'}})</script>
        </body></html>"""
    )


@router.post("/account-deletion/request")
def public_delete_request(req: PublicDeletionRequest):
    _ensure_public_request_table()
    email = str(req.email).strip().lower()
    now = int(time.time())
    with auth._db() as c:
        existing = c.execute(
            "SELECT id FROM account_deletion_requests WHERE email=? COLLATE NOCASE AND status='pending' ORDER BY id DESC LIMIT 1",
            (email,),
        ).fetchone()
        if not existing:
            c.execute(
                "INSERT INTO account_deletion_requests(email,requested_at,status) VALUES(?,?,'pending')",
                (email, now),
            )
    return {
        "ok": True,
        "message": "Deletion request received. JANUS will verify account ownership before deleting data.",
    }


_ensure_public_request_table()
