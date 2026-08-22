"""Normalize Stage-1 image artifacts and apply unified cost scope to chat."""
from __future__ import annotations

from fastapi import Request

import cost_governor as budget
import cost_governor_hooks

# Bootstrap imports this module after the chat/vision/image modules are loaded, so it
# is a stable point to install the centralized paid-call proxies without changing
# those feature implementations independently.
cost_governor_hooks.install()


def install(app) -> None:
    if getattr(app.state, "janus_image_response_compat", False):
        return
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
        with budget.scope(profile, "chat"):
            result = await impl(request=request, payload=payload)
        if isinstance(result, dict):
            image = result.get("generated_image") or result.get("image")
            if isinstance(image, dict):
                result["generated_image"] = image
                result.setdefault("image", image)
            result["cost_governor"] = budget.status(profile)
        return result

    paths={getattr(r,"path","") for r in app.router.routes}
    if "/desktop/cost-status" not in paths:
        @app.get("/desktop/cost-status", tags=["desktop"])
        def cost_status(username: str):
            return {"ok": True, **budget.status(username)}

    app.state.janus_cost_governor_enabled = True
    app.state.janus_image_response_compat = True
