"""Resilient JANUS bootstrap for Render.

Always exposes /health if the full JANUS application fails during import.
Also exposes minimal non-secret auth diagnostics when the main app loads.
"""
from __future__ import annotations

import os
import traceback
from fastapi import FastAPI
from fastapi.responses import JSONResponse

_startup_error = None
_startup_trace = None

try:
    # Normalize incompatible persistent account schemas before auth.py is imported.
    from auth_db_normalizer import normalize_legacy_accounts
    _auth_normalization = normalize_legacy_accounts()

    # Then catch partially-current legacy session/token tables. Older JANUS
    # schemas may contain account_id but still lack token_hash/expiry columns.
    # Those tables are preserved rather than deleted; auth.py recreates the
    # current tables immediately afterwards.
    from auth_schema_guard import guard_auth_schema, auth_schema_snapshot
    _auth_schema_guard = guard_auth_schema()

    from janus_dashboard import app as real_app
    import auth as auth_module
    app = real_app

    @app.middleware("http")
    async def preserve_google_auth_error(request, call_next):
        """Keep useful JANUS auth JSON visible to older Android builds."""
        response = await call_next(request)
        if request.url.path == "/auth/google" and response.status_code == 503:
            response.status_code = 409
            response.headers["X-JANUS-Original-Status"] = "503"
        return response

    @app.get("/diagnostics/auth-config")
    def auth_config():
        routes = {getattr(route, "path", "") for route in app.routes}
        return {
            "status": "ok",
            "main_app_loaded": True,
            "deployed_commit": os.getenv("RENDER_GIT_COMMIT", "unknown")[:40],
            "google_client_configured": bool(os.getenv("JANUS_GOOGLE_CLIENT_ID", "").strip()),
            "auth_module_google_client_configured": bool(getattr(auth_module, "GOOGLE_CLIENT_ID", "").strip()),
            "google_route_present": "/auth/google" in routes,
            "register_route_present": "/auth/register" in routes,
            "health_route_present": "/health" in routes,
            "auth_schema_normalization": _auth_normalization,
            "auth_schema_guard": _auth_schema_guard,
            "auth_schema": auth_schema_snapshot(),
        }
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
        return {
            "status": "degraded",
            "error": _startup_error,
            "traceback": _startup_trace,
            "python_version": os.sys.version.split()[0],
            "deployed_commit": os.getenv("RENDER_GIT_COMMIT", "unknown")[:40],
        }

    @app.get("/diagnostics/auth-config")
    def auth_config_degraded():
        return {
            "status": "degraded",
            "main_app_loaded": False,
            "deployed_commit": os.getenv("RENDER_GIT_COMMIT", "unknown")[:40],
            "google_client_configured": bool(os.getenv("JANUS_GOOGLE_CLIENT_ID", "").strip()),
            "auth_module_google_client_configured": False,
            "google_route_present": False,
            "register_route_present": False,
            "health_route_present": True,
            "startup_error": _startup_error,
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
