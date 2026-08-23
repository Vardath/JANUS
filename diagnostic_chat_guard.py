"""Deterministic diagnostic replies that keep server and device telemetry separate."""
from __future__ import annotations

from typing import Any, Callable

from core_sync import presence_for_profile


def _find(app, path: str, method: str) -> Callable[..., Any]:
    for route in app.router.routes:
        if getattr(route, "path", None) == path and method in getattr(route, "methods", set()):
            return route.endpoint
    raise RuntimeError(f"route missing: {method} {path}")


def _remove(app, path: str, method: str) -> None:
    app.router.routes[:] = [
        r for r in app.router.routes
        if not (getattr(r, "path", None) == path and method in getattr(r, "methods", set()))
    ]


def _looks_like_server_diagnostic(message: str) -> bool:
    m = str(message or "").strip().lower()
    # Research/connectivity questions must reach the real foreground research
    # path. They are not server-runtime telemetry diagnostics.
    research_words = ("internet", "web", "youtube", "search", "browse", "browser", "transcript", "caption", "url", "website")
    if any(x in m for x in research_words):
        return False
    server_words = ("server janus", "server diagnostic", "online janus diagnostic", "online diagnostic", "global janus diagnostic")
    diagnostic_words = ("diagnostic", "status", "health", "check")
    return any(x in m for x in server_words) or ("server" in m and any(x in m for x in diagnostic_words))


def _server_reply(runtime: dict[str, Any]) -> str:
    cores = runtime.get("cores") or {}
    cycles = {k: int((v or {}).get("cycle_count") or 0) for k, v in cores.items()}
    counts = list(cycles.values())
    min_cycle = min(counts) if counts else 0
    max_cycle = max(counts) if counts else 0
    active = sum(1 for v in cores.values() if (v or {}).get("awake"))
    pending = sum(int((v or {}).get("pending_messages") or 0) for v in cores.values())
    thread_alive = bool(runtime.get("server_runtime_thread_alive"))
    return (
        "JANUS server diagnostic\n\n"
        f"Status: {'Healthy / running' if thread_alive else 'Runtime thread not confirmed'}\n"
        f"Phase: {runtime.get('phase') or 'unknown'}\n"
        f"Server runtime thread: {'alive' if thread_alive else 'not confirmed'}\n"
        f"Server cores: {len(cores) or runtime.get('core_count') or 0}\n"
        f"Server cycle range: {min_cycle}–{max_cycle}\n"
        f"Server cores currently awake: {active}\n"
        f"Server pending routed items: {pending}\n"
        f"Server persistence: {'yes' if runtime.get('persistent_storage') else 'no'}\n"
        f"Authenticated device clients online: {int(runtime.get('remote_clients') or 0)}\n"
        f"Registered device clients: {int(runtime.get('registered_clients') or 0)}\n\n"
        "Provenance: server core counters above come only from the server runtime. "
        "Client counts come only from authenticated server presence records. "
        "No Android/local core cycle counters were substituted for server counters."
    )


def install(app, runtime):
    previous = _find(app, "/desktop/chat", "POST")
    _remove(app, "/desktop/chat", "POST")

    @app.post("/desktop/chat", tags=["desktop"])
    async def diagnostic_guard(payload: dict[str, Any]):
        message = str(payload.get("message") or payload.get("text") or "").strip()
        if _looks_like_server_diagnostic(message):
            try:
                thread = getattr(runtime, "_thread", None)
                if not thread or not thread.is_alive():
                    runtime.start()
            except Exception:
                pass
            state = runtime.status()
            state["server_runtime_thread_alive"] = bool(getattr(runtime, "_thread", None) and runtime._thread.is_alive())
            profile = str(payload.get("profile_id") or payload.get("username") or "").strip()
            clients = presence_for_profile(profile) if profile else []
            state["remote_clients"] = sum(1 for x in clients if x.get("online"))
            state["registered_clients"] = len(clients)
            return {
                "reply": _server_reply(state),
                "mode": "server_runtime_diagnostic",
                "server_runtime_evidence": True,
                "device_evidence_used": False,
                "stored": False,
            }
        return await previous(payload)
