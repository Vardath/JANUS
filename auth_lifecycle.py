"""Authentication lifecycle extensions for JANUS.

Keeps session revocation separate from auth.py so logout can be audited and
tested independently of registration/provider code.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header, HTTPException

import auth

router = APIRouter(prefix="/auth", tags=["auth"])


def _token(authorization: Optional[str]) -> str:
    token = auth._bearer(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    return token


@router.post("/logout")
def logout(authorization: Optional[str] = Header(default=None)):
    """Revoke only the bearer session used for this request."""
    token = _token(authorization)
    with auth._db() as c:
        cur = c.execute("DELETE FROM sessions WHERE token_hash=?", (auth._token_hash(token),))
    return {"ok": True, "revoked": bool(cur.rowcount)}


@router.post("/logout-all")
def logout_all(authorization: Optional[str] = Header(default=None)):
    """Revoke every active session for the authenticated account."""
    token = _token(authorization)
    account = auth.account_for_token(token)
    if account is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    with auth._db() as c:
        cur = c.execute("DELETE FROM sessions WHERE account_id=?", (int(account["id"]),))
    return {"ok": True, "revoked_sessions": max(0, int(cur.rowcount or 0))}
