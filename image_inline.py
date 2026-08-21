"""Authenticated base64 transport for generated images in WebView clients.

Native Windows/iOS clients use the normal binary /files/{id}/download route.
Android's existing bridge is JSON-only, so it receives the same account-bound
bytes as base64 without exposing a public or token-bearing image URL.
"""
from __future__ import annotations

import base64
from typing import Optional

from fastapi import APIRouter, Header, HTTPException

import auth
import attachment_api

router = APIRouter(prefix="/images", tags=["images"])


@router.get("/{file_id}/inline")
def inline_generated_image(file_id: str, authorization: Optional[str] = Header(default=None)):
    account = auth.require_account(authorization)
    attachment_api._init_db()
    with attachment_api._db() as c:
        row = c.execute(
            "SELECT * FROM janus_files WHERE id=? AND account_id=?",
            (file_id, int(account["id"])),
        ).fetchone()
    if not row:
        raise HTTPException(404, "Image not found")
    mime = str(row["mime_type"] or "")
    if not mime.startswith("image/"):
        raise HTTPException(415, "File is not an image")
    path = attachment_api.FILE_ROOT / row["storage_name"]
    if not path.is_file():
        raise HTTPException(410, "Stored image bytes are unavailable")
    data = path.read_bytes()
    return {
        "ok": True,
        "file_id": file_id,
        "mime_type": mime,
        "size_bytes": len(data),
        "data_base64": base64.b64encode(data).decode("ascii"),
    }
