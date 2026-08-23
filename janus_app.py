"""Authoritative JANUS ASGI application composition."""
from __future__ import annotations

import os

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
from foreground_web_bridge import install as install_forced_foreground_web
from url_media_ingest import install as install_url_media_ingest

_original_needs_web = curiosity_search_module._needs_web


def _janus_needs_web(message: str) -> bool:
    text = str(message or "").strip().lower()
    explicit_web_intent = (
        "youtube", "internet", "web", "website", "browse", "browser",
        "transcript", "caption", "search", "look up", "online",
        "connection working", "connectivity", "open this link", "open the link",
        "weather", "today's", "current temperature",
    )
    return any(term in text for term in explicit_web_intent) or _original_needs_web(message)


curiosity_search_module._needs_web = _janus_needs_web
install_forced_foreground_web(app, curiosity_search_module)
install_url_media_ingest(app, curiosity_search_module)

app.state.janus_url_media_ingestion_hardcoded = True
app.state.janus_foreground_web_intent_hardcoded = True
app.state.janus_forced_foreground_web_hardcoded = True
app.state.janus_api_model_normalized = True
