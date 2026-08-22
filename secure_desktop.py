"""Authenticated wrappers for JANUS desktop/private API routes.

Installed after the legacy desktop and runtime-messaging routes. It replaces
private routes with session-bound wrappers so the authenticated account, not a
client-supplied username/profile_id, selects the data partition.
"""
from __future__ import annotations

from typing import Any, Callable

from fastapi import HTTPException, Query, Request

from auth import account_for_token


PRIVATE_PATHS = {
    "/desktop/chat",
    "/desktop/observe",
    "/desktop/core-observe",
    "/desktop/cores",
    "/desktop/memory",
    "/desktop/activity",
    "/desktop/settings",
    "/desktop/home",
    "/desktop/messages",
    "/desktop/runtime-cores",
    "/desktop/deliberations",
    "/desktop/continuity",
    "/desktop/hive-budget",
    "/desktop/core-research-status",
    "/desktop/message-quality",
    "/desktop/self-assessment",
}


def _bearer_token(request: Request, payload: dict[str, Any] | None = None) -> str:
    auth = (request.headers.get("authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    if payload:
        token = str(payload.get("_janus_token") or "").strip()
        if token:
            return token
    token = str(request.query_params.get("_janus_token") or "").strip()
    return token


def _profile(request: Request, payload: dict[str, Any] | None = None) -> str:
    account = account_for_token(_bearer_token(request, payload))
    if not account:
        raise HTTPException(status_code=401, detail="Valid JANUS session required")
    return str(account["username"])


def _find(app, path: str, method: str) -> Callable[..., Any]:
    for route in app.router.routes:
        if getattr(route, "path", None) == path and method in getattr(route, "methods", set()):
            return route.endpoint
    raise RuntimeError(f"JANUS route missing before security install: {method} {path}")


def _find_optional(app, path: str, method: str) -> Callable[..., Any] | None:
    for route in app.router.routes:
        if getattr(route, "path", None) == path and method in getattr(route, "methods", set()):
            return route.endpoint
    return None


def _remove(app, path: str, method: str) -> None:
    app.router.routes[:] = [
        route for route in app.router.routes
        if not (getattr(route, "path", None) == path and method in getattr(route, "methods", set()))
    ]


def install(app) -> None:
    # Capture the already-installed implementation functions before replacing routes.
    chat_impl = _find(app, "/desktop/chat", "POST")
    observe_impl = _find(app, "/desktop/observe", "GET")
    cores_impl = _find(app, "/desktop/cores", "GET")
    memory_impl = _find(app, "/desktop/memory", "GET")
    activity_impl = _find(app, "/desktop/activity", "GET")
    settings_impl = _find(app, "/desktop/settings", "GET")
    home_impl = _find(app, "/desktop/home", "GET")
    messages_impl = _find(app, "/desktop/messages", "GET")
    runtime_impl = _find(app, "/desktop/runtime-cores", "GET")
    deliberations_impl = _find(app, "/desktop/deliberations", "GET")
    message_state_impl = _find(app, "/desktop/messages/{event_id}/state", "POST")

    # Phase 2 route inventory: these routes were historically profile-selected by
    # query/payload and therefore need the same authenticated partition binding.
    core_observe_impl = _find_optional(app, "/desktop/core-observe", "GET")
    hive_budget_impl = _find_optional(app, "/desktop/hive-budget", "GET")
    core_research_impl = _find_optional(app, "/desktop/core-research-status", "GET")
    message_quality_impl = _find_optional(app, "/desktop/message-quality", "GET")
    self_assessment_impl = _find_optional(app, "/desktop/self-assessment", "GET")
    continuity_list_impl = _find_optional(app, "/desktop/continuity", "GET")
    continuity_create_impl = _find_optional(app, "/desktop/continuity", "POST")
    continuity_state_impl = _find_optional(app, "/desktop/continuity/{item_id}/state", "POST")
    continuity_events_impl = _find_optional(app, "/desktop/continuity/{item_id}/events", "GET")

    required = [
        ("/desktop/chat", "POST"),
        ("/desktop/observe", "GET"),
        ("/desktop/cores", "GET"),
        ("/desktop/memory", "GET"),
        ("/desktop/activity", "GET"),
        ("/desktop/settings", "GET"),
        ("/desktop/home", "GET"),
        ("/desktop/messages", "GET"),
        ("/desktop/runtime-cores", "GET"),
        ("/desktop/deliberations", "GET"),
        ("/desktop/messages/{event_id}/state", "POST"),
    ]
    optional = [
        ("/desktop/core-observe", "GET", core_observe_impl),
        ("/desktop/hive-budget", "GET", hive_budget_impl),
        ("/desktop/core-research-status", "GET", core_research_impl),
        ("/desktop/message-quality", "GET", message_quality_impl),
        ("/desktop/self-assessment", "GET", self_assessment_impl),
        ("/desktop/continuity", "GET", continuity_list_impl),
        ("/desktop/continuity", "POST", continuity_create_impl),
        ("/desktop/continuity/{item_id}/state", "POST", continuity_state_impl),
        ("/desktop/continuity/{item_id}/events", "GET", continuity_events_impl),
    ]
    for path, method in required:
        _remove(app, path, method)
    for path, method, impl in optional:
        if impl is not None:
            _remove(app, path, method)

    @app.post("/desktop/chat", tags=["desktop"])
    async def secure_chat(request: Request, payload: dict[str, Any]):
        profile = _profile(request, payload)
        safe = dict(payload)
        safe["profile_id"] = profile
        safe["username"] = profile
        safe.pop("_janus_token", None)
        return await chat_impl(safe)

    @app.get("/desktop/observe", tags=["desktop"])
    def secure_observe(request: Request):
        return observe_impl(username=_profile(request))

    @app.get("/desktop/cores", tags=["desktop"])
    def secure_cores(request: Request):
        return cores_impl(username=_profile(request))

    @app.get("/desktop/memory", tags=["desktop"])
    def secure_memory(request: Request, limit: int = Query(default=80, ge=1, le=100)):
        return memory_impl(username=_profile(request), limit=limit)

    @app.get("/desktop/activity", tags=["desktop"])
    def secure_activity(request: Request, limit: int = Query(default=80, ge=1, le=100)):
        return activity_impl(username=_profile(request), limit=limit)

    @app.get("/desktop/settings", tags=["desktop"])
    def secure_settings(request: Request):
        return settings_impl(username=_profile(request))

    @app.get("/desktop/home", tags=["desktop"])
    def secure_home(request: Request):
        return home_impl(username=_profile(request))

    @app.get("/desktop/messages", tags=["desktop"])
    def secure_messages(
        request: Request,
        limit: int = Query(default=50, ge=1, le=100),
        include_dismissed: bool = Query(default=False),
    ):
        return messages_impl(
            username=_profile(request),
            limit=limit,
            include_dismissed=include_dismissed,
        )

    @app.get("/desktop/runtime-cores", tags=["desktop"])
    def secure_runtime_cores(request: Request):
        return runtime_impl(username=_profile(request))

    @app.get("/desktop/deliberations", tags=["desktop"])
    def secure_deliberations(request: Request, limit: int = Query(default=20, ge=1, le=100)):
        return deliberations_impl(username=_profile(request), limit=limit)

    @app.post("/desktop/messages/{event_id}/state", tags=["desktop"])
    def secure_message_state(event_id: int, request: Request, payload: dict[str, Any]):
        profile = _profile(request, payload)
        safe = dict(payload)
        safe["profile_id"] = profile
        safe["username"] = profile
        safe.pop("_janus_token", None)
        return message_state_impl(event_id=event_id, payload=safe)

    if core_observe_impl is not None:
        @app.get("/desktop/core-observe", tags=["desktop"])
        def secure_core_observe(
            request: Request,
            core: str = Query(default="all"),
            mode: str = Query(default="all"),
            limit: int = Query(default=200, ge=1, le=500),
        ):
            return core_observe_impl(username=_profile(request), core=core, mode=mode, limit=limit)

    if hive_budget_impl is not None:
        @app.get("/desktop/hive-budget", tags=["desktop"])
        def secure_hive_budget(request: Request):
            return hive_budget_impl(username=_profile(request))

    if core_research_impl is not None:
        @app.get("/desktop/core-research-status", tags=["desktop"])
        def secure_core_research_status(request: Request):
            return core_research_impl(username=_profile(request))

    if message_quality_impl is not None:
        @app.get("/desktop/message-quality", tags=["desktop"])
        def secure_message_quality(request: Request):
            return message_quality_impl(username=_profile(request))

    if self_assessment_impl is not None:
        @app.get("/desktop/self-assessment", tags=["desktop"])
        def secure_self_assessment(request: Request, limit: int = Query(default=20, ge=1, le=100)):
            _profile(request)  # require a valid account even though this telemetry is global
            return self_assessment_impl(limit=limit)

    if continuity_list_impl is not None:
        @app.get("/desktop/continuity", tags=["desktop"])
        def secure_continuity_list(
            request: Request,
            open_only: bool = Query(default=False),
            kind: str | None = Query(default=None),
            limit: int = Query(default=100, ge=1, le=500),
        ):
            return continuity_list_impl(username=_profile(request), open_only=open_only, kind=kind, limit=limit)

    if continuity_create_impl is not None:
        @app.post("/desktop/continuity", tags=["desktop"])
        def secure_continuity_create(request: Request, payload: dict[str, Any]):
            profile = _profile(request, payload)
            safe = dict(payload)
            safe["profile_id"] = profile
            safe["username"] = profile
            safe.pop("_janus_token", None)
            return continuity_create_impl(payload=safe)

    if continuity_state_impl is not None:
        @app.post("/desktop/continuity/{item_id}/state", tags=["desktop"])
        def secure_continuity_state(item_id: int, request: Request, payload: dict[str, Any]):
            profile = _profile(request, payload)
            safe = dict(payload)
            safe["profile_id"] = profile
            safe["username"] = profile
            safe.pop("_janus_token", None)
            return continuity_state_impl(item_id=item_id, payload=safe)

    if continuity_events_impl is not None:
        @app.get("/desktop/continuity/{item_id}/events", tags=["desktop"])
        def secure_continuity_events(
            item_id: int,
            request: Request,
            limit: int = Query(default=100, ge=1, le=500),
        ):
            return continuity_events_impl(item_id=item_id, username=_profile(request), limit=limit)

    app.state.janus_desktop_profile_routes_session_bound = True
