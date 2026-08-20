"""Resilient JANUS bootstrap for Render.

Always exposes /health even if the full JANUS application fails during import.
This prevents opaque gateway 502s and provides a minimal safe diagnostic.
"""
from __future__ import annotations

import os
import traceback
from fastapi import FastAPI
from fastapi.responses import JSONResponse

_startup_error = None
_startup_trace = None

try:
    from janus_dashboard import app as real_app
    app = real_app
except Exception as exc:  # keep Render reachable for diagnosis
    _startup_error = f"{type(exc).__name__}: {exc}"
    _startup_trace = traceback.format_exc(limit=12)
    app = FastAPI(title="JANUS bootstrap", version="degraded")

    @app.get("/health")
    def health():
        return JSONResponse(
            status_code=200,
            content={
                "status": "degraded",
                "service": "janus-global-core",
                "main_app_loaded": False,
                "startup_error": _startup_error,
            },
        )

    @app.get("/diagnostics/startup-error")
    def startup_error():
        # No environment values or secrets are returned.
        return {
            "status": "degraded",
            "error": _startup_error,
            "traceback": _startup_trace,
            "python_version": os.sys.version.split()[0],
        }

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    def unavailable(path: str):
        return JSONResponse(
            status_code=503,
            content={
                "detail": "JANUS server startup is degraded. Please try again shortly.",
                "startup_error": _startup_error,
            },
        )
