"""Resilient JANUS bootstrap for Render.

Public health/diagnostic routes expose only operational booleans. Detailed schema
and traceback diagnostics require the server admin token so deployment failures
remain diagnosable without publishing internals.
"""
from __future__ import annotations

import os
import secrets
import sqlite3
import traceback
from typing import Optional
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse

_startup_error = None
_startup_trace = None


def _admin_token(authorization: Optional[str], x_janus_admin_token: Optional[str]) -> str:
    if x_janus_admin_token:
        return x_janus_admin_token.strip()
    auth = (authorization or "").strip()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return ""


def _require_admin(authorization: Optional[str], x_janus_admin_token: Optional[str]) -> None:
    expected = os.getenv("JANUS_ACCESS_TOKEN", "").strip()
    supplied = _admin_token(authorization, x_janus_admin_token)
    if not expected or not supplied or not secrets.compare_digest(expected, supplied):
        raise HTTPException(status_code=401, detail="JANUS admin diagnostics token required")


try:
    from auth_db_normalizer import normalize_legacy_accounts
    _auth_normalization = normalize_legacy_accounts()

    from auth_schema_guard import guard_auth_schema, auth_schema_snapshot
    _auth_schema_guard = guard_auth_schema()

    from janus_dashboard import app as real_app
    import auth as auth_module
    import interface_chat as interface_chat_module
    from auth_lifecycle import router as auth_lifecycle_router
    from auth_rate_limit import install as install_auth_rate_limit
    from attachment_api import router as attachment_router
    from attachment_retention import install_storage_auditor
    from attachment_chat import install as install_attachment_chat
    from image_generation import router as image_generation_router, install_chat_image_bridge
    from image_inline import router as image_inline_router
    from image_response_compat import install as install_image_response_compat
    from chat_receipt_security import install as install_chat_receipt_security
    from maintenance_review import install as install_maintenance_review, status as maintenance_status, run_review as run_maintenance_review
    from src.janus_sleep_cycle import janus_sleep_cycle
    app = real_app
    app.include_router(auth_lifecycle_router)
    app.include_router(attachment_router)
    app.include_router(image_generation_router)
    app.include_router(image_inline_router)
    install_storage_auditor(app, janus_sleep_cycle)
    install_attachment_chat(app, janus_sleep_cycle)
    install_chat_image_bridge(app, interface_chat_module)
    install_image_response_compat(app)
    install_chat_receipt_security(interface_chat_module)
    install_auth_rate_limit(app)
    install_maintenance_review(app, janus_sleep_cycle)

    @app.middleware("http")
    async def preserve_google_auth_error(request, call_next):
        """Keep useful JANUS auth JSON visible to older Android builds."""
        response = await call_next(request)
        if request.url.path == "/auth/google" and response.status_code == 503:
            response.status_code = 409
            response.headers["X-JANUS-Original-Status"] = "503"
        return response

    def _runtime_health_snapshot():
        db_path = os.getenv("JANUS_DB_PATH", "/data/janus.sqlite3")
        db_ok = False
        quick_check = None
        try:
            with sqlite3.connect(db_path, timeout=5) as c:
                quick_check = c.execute("PRAGMA quick_check").fetchone()[0]
                c.execute("BEGIN IMMEDIATE")
                c.execute("ROLLBACK")
                db_ok = str(quick_check).lower() == "ok"
        except Exception:
            db_ok = False

        try:
            runtime = janus_sleep_cycle.status()
        except Exception:
            runtime = {}

        auth_schema = auth_schema_snapshot()
        required = {
            "accounts": {"id", "username", "email", "password_hash"},
            "sessions": {"token_hash", "account_id", "expires_at"},
            "auth_tokens": {"token_hash", "account_id", "purpose", "expires_at"},
        }
        schema_ok = True
        try:
            for table, cols in required.items():
                present = set(auth_schema.get(table, {}).get("columns", []))
                if not cols.issubset(present):
                    schema_ok = False
                    break
        except Exception:
            schema_ok = False

        core_persistent = bool(runtime.get("persistent_storage")) if isinstance(runtime, dict) else False
        healthy = bool(db_ok and schema_ok and core_persistent)
        return {
            "status": "ok" if healthy else "degraded",
            "service": "janus-global-core",
            "main_app_loaded": True,
            "deployed_commit": os.getenv("RENDER_GIT_COMMIT", "unknown")[:40],
            "database_ok": db_ok,
            "database_quick_check_ok": str(quick_check).lower() == "ok" if quick_check is not None else False,
            "auth_schema_ok": schema_ok,
            "core_persistence_ok": core_persistent,
            "core_phase": runtime.get("phase") if isinstance(runtime, dict) else None,
            "core_count": runtime.get("core_count") if isinstance(runtime, dict) else None,
            "remote_clients": runtime.get("remote_clients") if isinstance(runtime, dict) else None,
            "background_external_api_budget_used": runtime.get("external_api_budget_used", 0) if isinstance(runtime, dict) else None,
            "chat_receipt_profile_guard": bool(getattr(interface_chat_module, "_profile_receipt_guard_installed", False)),
            "auth_rate_limit_enabled": True,
            "deliberation_tasks_enabled": True,
            "file_sharing_enabled": True,
            "file_chat_grounding_enabled": bool(getattr(app.state, "janus_attachment_chat_bridge", False)),
            "file_storage_auditor_enabled": True,
            "lightweight_image_generation_enabled": True,
            "image_inline_transport_enabled": True,
            "background_multi_core_image_generation_enabled": False,
            "quarterly_maintenance_review_enabled": bool(getattr(app.state, "janus_maintenance_review_installed", False)),
        }

    @app.get("/diagnostics/runtime-health")
    def runtime_health():
        return _runtime_health_snapshot()

    @app.get("/diagnostics/auth-config")
    def auth_config():
        routes = {getattr(route, "path", "") for route in app.routes}
        return {
            "status": "ok",
            "main_app_loaded": True,
            "deployed_commit": os.getenv("RENDER_GIT_COMMIT", "unknown")[:40],
            "google_client_configured": bool(os.getenv("JANUS_GOOGLE_CLIENT_ID", "").strip()),
            "google_route_present": "/auth/google" in routes,
            "register_route_present": "/auth/register" in routes,
            "login_route_present": "/auth/login" in routes,
            "logout_route_present": "/auth/logout" in routes,
            "logout_all_route_present": "/auth/logout-all" in routes,
            "runtime_health_route_present": "/diagnostics/runtime-health" in routes,
            "deliberation_route_present": "/desktop/deliberations" in routes,
            "file_upload_route_present": "/files/upload" in routes,
            "file_storage_status_route_present": "/files/storage/status" in routes,
            "file_audit_route_present": "/files/audit/recent" in routes,
            "file_chat_grounding_enabled": bool(getattr(app.state, "janus_attachment_chat_bridge", False)),
            "image_generate_route_present": "/images/generate" in routes,
            "image_usage_route_present": "/images/usage" in routes,
            "image_inline_route_present": any(path.startswith("/images/{file_id}/inline") for path in routes),
            "background_multi_core_image_generation_enabled": False,
            "auth_rate_limit_enabled": True,
            "quarterly_maintenance_review_enabled": bool(getattr(app.state, "janus_maintenance_review_installed", False)),
        }

    @app.get("/diagnostics/maintenance")
    def maintenance_detail(
        authorization: Optional[str] = Header(default=None),
        x_janus_admin_token: Optional[str] = Header(default=None),
    ):
        _require_admin(authorization, x_janus_admin_token)
        return maintenance_status()

    @app.post("/diagnostics/maintenance/run")
    def maintenance_run(
        authorization: Optional[str] = Header(default=None),
        x_janus_admin_token: Optional[str] = Header(default=None),
    ):
        _require_admin(authorization, x_janus_admin_token)
        return run_maintenance_review(janus_sleep_cycle, "manual-admin-request")

    @app.get("/diagnostics/auth-detail")
    def auth_detail(
        authorization: Optional[str] = Header(default=None),
        x_janus_admin_token: Optional[str] = Header(default=None),
    ):
        _require_admin(authorization, x_janus_admin_token)
        return {
            "status": "ok",
            "deployed_commit": os.getenv("RENDER_GIT_COMMIT", "unknown")[:40],
            "auth_module_google_client_configured": bool(getattr(auth_module, "GOOGLE_CLIENT_ID", "").strip()),
            "chat_receipt_profile_guard": bool(getattr(interface_chat_module, "_profile_receipt_guard_installed", False)),
            "auth_schema_normalization": _auth_normalization,
            "auth_schema_guard": _auth_schema_guard,
            "auth_schema": auth_schema_snapshot(),
        }
except Exception as exc:
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
            },
        )

    @app.get("/diagnostics/runtime-health")
    def runtime_health_degraded():
        return {
            "status": "degraded",
            "service": "janus-global-core",
            "main_app_loaded": False,
            "deployed_commit": os.getenv("RENDER_GIT_COMMIT", "unknown")[:40],
        }

    @app.get("/diagnostics/startup-error")
    def startup_error(
        authorization: Optional[str] = Header(default=None),
        x_janus_admin_token: Optional[str] = Header(default=None),
    ):
        _require_admin(authorization, x_janus_admin_token)
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
            "google_route_present": False,
            "register_route_present": False,
            "login_route_present": False,
            "logout_route_present": False,
            "logout_all_route_present": False,
            "runtime_health_route_present": True,
            "deliberation_route_present": False,
            "file_upload_route_present": False,
            "file_storage_status_route_present": False,
            "file_audit_route_present": False,
            "file_chat_grounding_enabled": False,
            "image_generate_route_present": False,
            "image_usage_route_present": False,
            "image_inline_route_present": False,
            "background_multi_core_image_generation_enabled": False,
            "auth_rate_limit_enabled": False,
        }

    @app.get("/diagnostics/auth-detail")
    def auth_detail_degraded(
        authorization: Optional[str] = Header(default=None),
        x_janus_admin_token: Optional[str] = Header(default=None),
    ):
        _require_admin(authorization, x_janus_admin_token)
        return {
            "status": "degraded",
            "main_app_loaded": False,
            "deployed_commit": os.getenv("RENDER_GIT_COMMIT", "unknown")[:40],
            "startup_error": _startup_error,
        }

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    def unavailable(path: str):
        return JSONResponse(
            status_code=503,
            content={"detail": "JANUS server startup is degraded. Please try again shortly."},
        )
