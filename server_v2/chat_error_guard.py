from __future__ import annotations

import re
from starlette.responses import JSONResponse


def _safe_message(exc: Exception) -> str:
    text = str(exc or "")[:600]
    # Redact likely secrets/tokens and local filesystem details from diagnostic output.
    text = re.sub(r"(?i)(bearer|token|password|api[_ -]?key)\s*[:=]?\s*[^\s,;]+", r"\1=[redacted]", text)
    text = re.sub(r"/(?:data|home|tmp)/[^\s,;]+", "[path]", text)
    return text


def install(app) -> None:
    """Guard unhandled Chat exceptions while allowing bounded CI diagnosis.

    Ordinary clients receive only a generic 503. The release smoke runner may opt into
    a bounded class/message using X-JANUS-Live-Smoke: 1. No traceback is returned.
    """
    @app.middleware("http")
    async def janus_chat_error_guard(request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            if request.url.path != "/desktop/chat":
                raise
            diagnostic = request.headers.get("x-janus-live-smoke", "") == "1"
            try:
                # Avoid importing application modules here; this guard must itself be
                # dependable even when Chat internals are what failed.
                import logging
                logging.getLogger("janus.chat").exception("Unhandled /desktop/chat failure")
            except Exception:
                pass
            if diagnostic:
                return JSONResponse(
                    status_code=500,
                    content={
                        "detail": "JANUS chat processing failed",
                        "stage": "desktop_chat",
                        "error_class": exc.__class__.__name__,
                        "error": _safe_message(exc),
                    },
                )
            return JSONResponse(
                status_code=503,
                content={"detail": "JANUS chat processing is temporarily unavailable; local state remains intact."},
            )
