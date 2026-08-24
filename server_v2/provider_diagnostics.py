from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Header

from . import auth

router = APIRouter()


def _safe_error(exc: Exception) -> dict:
    body = getattr(exc, "body", None)
    code = getattr(exc, "code", None)
    status = getattr(exc, "status_code", None)
    message = str(exc)
    if isinstance(body, dict):
        err = body.get("error") if isinstance(body.get("error"), dict) else body
        code = code or err.get("code")
        message = str(err.get("message") or message)
    # Provider diagnostics must never return credentials, request headers or raw
    # request bodies. The provider's short public error message is sufficient.
    return {
        "ok": False,
        "error_type": type(exc).__name__,
        "status_code": status,
        "code": code,
        "message": message[:700],
    }


@router.get("/diagnostics/provider-status")
def provider_status(authorization: Optional[str] = Header(default=None)):
    auth.require_account(authorization)
    key_present = bool(os.getenv("OPENAI_API_KEY", "").strip())
    text = {"ok": False, "error_type": "NotConfigured", "message": "OPENAI_API_KEY is not configured"}
    if key_present:
        try:
            from openai import OpenAI
            model = os.getenv("JANUS_MODEL_LUNA", "gpt-5.6-luna")
            response = OpenAI(api_key=os.environ["OPENAI_API_KEY"]).responses.create(
                model=model,
                input="Reply with exactly: JANUS_PROVIDER_OK",
            )
            out = (getattr(response, "output_text", "") or "").strip()
            text = {"ok": out == "JANUS_PROVIDER_OK", "model": model, "response": out[:100]}
        except Exception as exc:
            text = _safe_error(exc)
            text["model"] = os.getenv("JANUS_MODEL_LUNA", "gpt-5.6-luna")

    return {
        "ok": bool(text.get("ok")),
        "key_present": key_present,
        "text_provider": text,
        "image_model": os.getenv("JANUS_IMAGE_MODEL", "gpt-image-1"),
        "image_quality": os.getenv("JANUS_IMAGE_QUALITY", "medium"),
        "note": "This endpoint exposes provider health/error classification only; it never returns credentials.",
    }
