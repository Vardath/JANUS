from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Header

from . import auth, identity

router = APIRouter()


@router.get("/desktop/identity-core")
def identity_core(authorization: Optional[str] = Header(default=None)):
    account = auth.require_account(authorization)
    item = identity.ensure(int(account["id"]))
    return {
        "ok": True,
        "profile": account["username"],
        "identity_core": item,
        "protected": True,
        "ordinary_conversation_can_overwrite": False,
    }
