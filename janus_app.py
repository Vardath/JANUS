"""Authoritative JANUS ASGI application composition.

This module intentionally performs runtime composition through normal Python
imports rather than build-time source patching. Uvicorn starts this module only
after bootstrap has constructed the application, then URL/media ingestion and
foreground web-intent hardening are installed directly against the live
curiosity module used by Interface chat.
"""
from __future__ import annotations

from bootstrap import app
import curiosity_search as curiosity_search_module
from url_media_ingest import install as install_url_media_ingest

# Hard-coded foreground web intent. The original curiosity heuristic predates
# the YouTube/browser capability work and did not classify words such as
# "youtube", "transcript", "browse" or "connection" as requiring live web.
# That allowed Interface to answer capability questions from telemetry/context
# instead of actually exercising the web tool. Keep the original heuristic and
# broaden it here at the authoritative runtime composition layer so this cannot
# be lost when older modules are reconstructed or product patches are composed.
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
    )
    return any(term in text for term in explicit_web_intent) or _original_needs_web(message)


curiosity_search_module._needs_web = _janus_needs_web

# Hard-coded product capability: public URL ingestion and best-effort YouTube
# transcript retrieval are part of the application runtime, not an optional
# text-patch step. install() is idempotent.
install_url_media_ingest(app, curiosity_search_module)

# Explicit markers for diagnostics/tests without exposing private state.
app.state.janus_url_media_ingestion_hardcoded = True
app.state.janus_foreground_web_intent_hardcoded = True
