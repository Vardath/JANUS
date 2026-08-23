"""Authoritative JANUS ASGI application composition.

This module intentionally performs runtime composition through normal Python
imports rather than build-time source patching. Uvicorn starts this module only
after the runtime model configuration is normalized, then the hard-coded live
web bridge and URL/media ingestion are installed directly against the live
curiosity module used by Interface chat.
"""
from __future__ import annotations

import os

# The ChatGPT product/model name is not necessarily an OpenAI API model ID.
# Older JANUS configuration used gpt-5.6 / gpt-5.6-luna, which can make both the
# final Interface call and foreground web-search call fail and then fall back to
# telemetry-like notes. Normalize unsupported project-era aliases BEFORE
# bootstrap imports any module that reads these environment variables.
def _normalize_api_model_env() -> None:
    keys = (
        "JANUS_MODEL",
        "JANUS_CORE_FOREGROUND_MODEL",
        "JANUS_BACKGROUND_MODEL",
        "JANUS_CURIOSITY_MODEL",
    )
    for key in keys:
        value = str(os.environ.get(key, "") or "").strip().lower()
        if not value or value in {"gpt-5.6", "gpt-5.6-luna", "gpt-5.6-sol"}:
            os.environ[key] = "gpt-5"
    os.environ["JANUS_CORE_MODEL_CONSULT"] = "1"
    os.environ["JANUS_FOREGROUND_WEB"] = "1"
    os.environ["JANUS_CURIOSITY_WEB"] = "1"


_normalize_api_model_env()

from bootstrap import app
import curiosity_search as curiosity_search_module
from foreground_web_bridge import install as install_forced_foreground_web
from url_media_ingest import install as install_url_media_ingest

# Hard-coded foreground web intent. The original curiosity heuristic predates
# the YouTube/browser capability work and did not classify words such as
# "youtube", "transcript", "browse" or "connection" as requiring live web.
_original_needs_web = curiosity_search_module._needs_web


def _janus_needs_web(message: str) -> bool:
    text = str(message or "").strip().lower()
    explicit_web_intent = (
        "youtube",
        "internet",
        "web",
        "website",
        "browse",
        "browser",
        "transcript",
        "caption",
        "search",
        "look up",
        "online",
        "connection working",
        "connectivity",
        "open this link",
        "open the link",
        "weather",
        "today's",
        "current temperature",
    )
    return any(term in text for term in explicit_web_intent) or _original_needs_web(message)


curiosity_search_module._needs_web = _janus_needs_web

# Install forced web first. URL/media ingestion then wraps it, so direct URLs are
# retrieved/cached/provenanced before the enriched request enters live research.
install_forced_foreground_web(app, curiosity_search_module)
install_url_media_ingest(app, curiosity_search_module)

# Explicit markers for diagnostics/tests without exposing private state.
app.state.janus_url_media_ingestion_hardcoded = True
app.state.janus_foreground_web_intent_hardcoded = True
app.state.janus_forced_foreground_web_hardcoded = True
app.state.janus_api_model_normalized = True
