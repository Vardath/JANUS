"""Normalize image artifacts, apply unified cost scope, preserve Message threads, and activate visual/research/reliability policy."""
from __future__ import annotations

import os
from fastapi import Request

import cost_governor as budget
import cost_governor_hooks
import dashboard_api
import proactive_threads
import image_generation
import visual_explanation
import visual_deliberation
import research_workspace
import reliability_audit
import secure_desktop

cost_governor_hooks.install()
visual_explanation.install(image_generation)


def _reply_event_id(payload: dict):
    for key in ("reply_to_message_id", "proactive_event_id", "message_event_id"):
        raw = payload.get(key)
        if raw is not None and str(raw).strip():
            try:
                return int(raw)
            except Exception:
                return None
    return None


def _authenticated_profile(request: Request, payload: dict | None = None) -> str:
    """Resolve the only profile allowed to receive profile-scoped side effects."""
    return secure_desktop._profile(request, payload)


def _authenticated_payload(request: Request, payload: dict) -> tuple[str, dict]:
    """Return a copy bound to the authenticated account, never client identity."""
    profile = _authenticated_profile(request, payload)
    safe = dict(payload)
    safe["profile_id"] = profile
    safe["username"] = profile
    return profile, safe


def install(app) -> None:
    if getattr(app.state, "janus_image_response_compat", False):
        return
    proactive_threads.install(app)
    paths = {getattr(r, "path", "") for r in app.router.routes}
    if "/visual-deliberations" not in paths:
        app.include_router(visual_deliberation.router)
    if "/research/workspace" not in paths:
        app.include_router(research_workspace.router)
    if "/reliability/status" not in paths:
        app.include_router(reliability_audit.router)

    owner_profile = (os.getenv("JANUS_RESEARCH_OWNER_PROFILE", "").strip()
                     or os.getenv("JANUS_MAINTENANCE_OWNER_PROFILE", "").strip())
    if owner_profile:
        try:
            research_workspace.seed_janus_program(owner_profile)
        except Exception:
            pass

    route = next(
        (r for r in app.router.routes if getattr(r, "path", None) == "/desktop/chat" and "POST" in getattr(r, "methods", set())),
        None,
    )
    if route is None:
        raise RuntimeError("image-enabled /desktop/chat route missing before compatibility install")
    impl = route.endpoint
    app.router.routes[:] = [
        r for r in app.router.routes
        if not (getattr(r, "path", None) == "/desktop/chat" and "POST" in getattr(r, "methods", set()))
    ]

    @app.post("/desktop/chat", tags=["desktop"])
    async def normalized_image_chat(request: Request, payload: dict):
        # This wrapper is installed after secure_desktop. Authenticate before any
        # thread, memory, research or cost-ledger access so a forged profile_id can
        # never create/read side effects in another account's partition.
        profile, safe = _authenticated_payload(request, payload)
        message = str(safe.get("message") or safe.get("text") or "").strip()
        thread_context, thread = proactive_threads.format_chat_context(profile, message, _reply_event_id(safe))
        if thread_context:
            dashboard_api._store(profile, "thread_context", thread_context, "proactive_thread_context", "working")
        research_context = research_workspace.workspace_context(profile)
        if not research_context.startswith("No JANUS research workspace"):
            dashboard_api._store(profile, "research_context", research_context, "research_workspace_context", "working")
        with budget.scope(profile, "chat"):
            result = await impl(request=request, payload=safe)
        if isinstance(result, dict):
            image = result.get("generated_image") or result.get("image")
            if isinstance(image, dict):
                result["generated_image"] = image
                result.setdefault("image", image)
            result["cost_governor"] = budget.status(profile)
            result["research_workspace_active"] = not research_context.startswith("No JANUS research workspace")
            if thread:
                result["proactive_thread"] = {
                    "event_id": thread.get("event_id"),
                    "thread_key": thread.get("thread_key"),
                    "thread_type": thread.get("thread_type"),
                    "title": thread.get("title"),
                    "continuity_item_id": thread.get("continuity_item_id"),
                }
        return result

    paths={getattr(r,"path","") for r in app.router.routes}
    if "/desktop/cost-status" not in paths:
        @app.get("/desktop/cost-status", tags=["desktop"])
        def cost_status(request: Request):
            profile = _authenticated_profile(request)
            return {"ok": True, **budget.status(profile)}

    app.state.janus_cost_governor_enabled = True
    app.state.janus_proactive_thread_chat_enabled = True
    app.state.janus_visual_explanation_enabled = True
    app.state.janus_visual_deliberation_scaffolding_enabled = True
    app.state.janus_research_workspace_enabled = True
    app.state.janus_reliability_audit_enabled = True
    app.state.janus_profile_boundary_hardening_enabled = True
    app.state.janus_background_multi_core_image_generation_enabled = False
    app.state.janus_image_response_compat = True
