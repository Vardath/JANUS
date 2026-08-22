"""Normalize image artifacts, apply unified cost scope, and preserve Message threads."""
from __future__ import annotations

from fastapi import Request

import cost_governor as budget
import cost_governor_hooks
import dashboard_api
import proactive_threads

# Bootstrap imports this module after the chat/vision/image modules are loaded, so it
# is a stable point to install cross-cutting paid-call and thread-continuity policy.
cost_governor_hooks.install()


def _reply_event_id(payload: dict):
    for key in ("reply_to_message_id", "proactive_event_id", "message_event_id"):
        raw = payload.get(key)
        if raw is not None and str(raw).strip():
            try:
                return int(raw)
            except Exception:
                return None
    return None


def install(app) -> None:
    if getattr(app.state, "janus_image_response_compat", False):
        return
    proactive_threads.install(app)
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
        profile = str(payload.get("profile_id") or payload.get("username") or "local-user")
        message = str(payload.get("message") or payload.get("text") or "").strip()
        thread_context, thread = proactive_threads.format_chat_context(profile, message, _reply_event_id(payload))
        # Store a bounded process-context record rather than changing the user's text.
        # interface_chat's normal recent-context path will see it later in this turn.
        if thread_context:
            dashboard_api._store(profile, "thread_context", thread_context, "proactive_thread_context", "working")
        with budget.scope(profile, "chat"):
            result = await impl(request=request, payload=payload)
        if isinstance(result, dict):
            image = result.get("generated_image") or result.get("image")
            if isinstance(image, dict):
                result["generated_image"] = image
                result.setdefault("image", image)
            result["cost_governor"] = budget.status(profile)
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
        def cost_status(username: str):
            return {"ok": True, **budget.status(username)}

    app.state.janus_cost_governor_enabled = True
    app.state.janus_proactive_thread_chat_enabled = True
    app.state.janus_image_response_compat = True
