"""Authoritative JANUS ASGI application composition."""
from __future__ import annotations

import inspect
import os
from typing import Any

from fastapi import Request

# Keep JANUS on current OpenAI API model IDs. Luna is the economical default;
# foreground research can fall back through Terra/Sol/base GPT-5.6.
def _normalize_api_model_env() -> None:
    aliases = {
        "gpt-5": "gpt-5.6-luna",
        "gpt-5-mini": "gpt-5.6-luna",
    }
    defaults = {
        "JANUS_MODEL": "gpt-5.6-luna",
        "JANUS_CORE_FOREGROUND_MODEL": "gpt-5.6-luna",
        "JANUS_BACKGROUND_MODEL": "gpt-5.6-luna",
        "JANUS_CURIOSITY_MODEL": "gpt-5.6-luna",
    }
    for key, default in defaults.items():
        value = str(os.environ.get(key, "") or "").strip().lower()
        os.environ[key] = aliases.get(value, value or default)
    os.environ["JANUS_CORE_MODEL_CONSULT"] = "1"
    os.environ["JANUS_FOREGROUND_WEB"] = "1"
    os.environ["JANUS_CURIOSITY_WEB"] = "1"


_normalize_api_model_env()

from bootstrap import app
import curiosity_search as curiosity_search_module
import secure_desktop
from foreground_web_bridge import install as install_forced_foreground_web
from url_media_ingest import install as install_url_media_ingest

_original_needs_web = curiosity_search_module._needs_web


def _janus_needs_web(message: str) -> bool:
    text = str(message or "").strip().lower()
    explicit_web_intent = (
        "youtube", "internet", "web", "website", "browse", "browser",
        "transcript", "caption", "search", "look up", "online",
        "connection working", "connectivity", "open this link", "open the link",
        "weather", "today's", "todays", "current temperature", "current weather",
    )
    return any(term in text for term in explicit_web_intent) or _original_needs_web(message)


curiosity_search_module._needs_web = _janus_needs_web
install_forced_foreground_web(app, curiosity_search_module)
install_url_media_ingest(app, curiosity_search_module)


def _find_chat_route():
    for route in app.router.routes:
        if getattr(route, "path", None) == "/desktop/chat" and "POST" in getattr(route, "methods", set()):
            return route.endpoint
    raise RuntimeError("JANUS /desktop/chat route missing")


def _remove_chat_route() -> None:
    app.router.routes[:] = [
        route for route in app.router.routes
        if not (getattr(route, "path", None) == "/desktop/chat" and "POST" in getattr(route, "methods", set()))
    ]


def _research_reply(result: dict[str, Any]) -> str:
    text = str(result.get("result") or "").strip()
    sources = result.get("sources") or []
    if sources:
        rows = []
        for source in sources[:6]:
            if not isinstance(source, dict):
                continue
            title = str(source.get("title") or "Source").strip()
            url = str(source.get("url") or "").strip()
            if url:
                rows.append(f"- {title}: {url}")
        if rows:
            text += "\n\nSources actually retrieved:\n" + "\n".join(rows)
    return text


async def _call_chat_impl(impl, request: Request, payload: dict[str, Any]):
    params = inspect.signature(impl).parameters
    result = impl(request=request, payload=payload) if "request" in params else impl(payload=payload)
    if inspect.isawaitable(result):
        result = await result
    return result


def _install_authoritative_chat_research_gate() -> None:
    """Final route-level guarantee that live research reaches normal chat safely.

    This gate is installed after the authenticated/private route stack. It therefore
    must preserve the same account boundary: client-supplied profile selectors are
    never authorization, and even explicit web research is bound to the authenticated
    JANUS account before any profile-scoped work occurs.
    """
    previous = _find_chat_route()
    _remove_chat_route()

    @app.post("/desktop/chat", tags=["desktop"])
    async def authoritative_chat(request: Request, payload: dict[str, Any]):
        # Authenticate first and overwrite all client identity selectors. This is
        # deliberately duplicated at the outermost gate so later composition cannot
        # accidentally reopen the cross-account boundary.
        profile = secure_desktop._profile(request, payload)
        safe = dict(payload)
        safe["profile_id"] = profile
        safe["username"] = profile
        safe.pop("_janus_token", None)

        message = str(safe.get("message") or safe.get("text") or "").strip()
        if message and _janus_needs_web(message):
            result = curiosity_search_module.foreground_deliberate(profile, message)
            if inspect.isawaitable(result):
                result = await result
            if isinstance(result, dict) and result.get("retrieved") and result.get("web"):
                reply = _research_reply(result)
                if reply:
                    return {
                        "reply": reply,
                        "profile": profile,
                        "mode": "authoritative_live_web",
                        "web_attempted": True,
                        "web": True,
                        "retrieved": True,
                        "actual_model": result.get("actual_model"),
                        "sources": result.get("sources") or [],
                        "foreground_research": result,
                        "stored": False,
                        "client_message_id": str(safe.get("client_message_id") or "")[:128],
                    }
            # A genuine provider/tool failure should be reported as such. Do not
            # fall through to telemetry and falsely claim no web capability exists.
            if isinstance(result, dict) and result.get("web_attempted"):
                diagnostic = str(result.get("error") or "web_search_failed")
                return {
                    "reply": "I attempted live web research for this request, but the web provider/tool call failed this turn. Diagnostic: " + diagnostic[:1200],
                    "profile": profile,
                    "mode": "authoritative_live_web_error",
                    "web_attempted": True,
                    "web": False,
                    "retrieved": False,
                    "error": diagnostic,
                    "client_message_id": str(safe.get("client_message_id") or "")[:128],
                }

        return await _call_chat_impl(previous, request, safe)


_install_authoritative_chat_research_gate()

app.state.janus_url_media_ingestion_hardcoded = True
app.state.janus_foreground_web_intent_hardcoded = True
app.state.janus_forced_foreground_web_hardcoded = True
app.state.janus_api_model_normalized = True
app.state.janus_authoritative_chat_research_gate = True
app.state.janus_authoritative_chat_auth_bound = True
