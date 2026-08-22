"""Normalize Stage-1 image artifacts in authenticated chat responses."""
from __future__ import annotations

from fastapi import Request


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
        result = await impl(request=request, payload=payload)
        if isinstance(result, dict):
            image = result.get("generated_image") or result.get("image")
            if isinstance(image, dict):
                result["generated_image"] = image
                result.setdefault("image", image)
        return result

    app.state.janus_image_response_compat = True
