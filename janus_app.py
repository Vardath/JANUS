"""Authoritative JANUS ASGI application composition.

This module intentionally performs runtime composition through normal Python
imports rather than build-time source patching.  Uvicorn starts this module
only after bootstrap has constructed the application, then URL/media ingestion
is installed directly against the live curiosity module used by Interface chat.
"""
from __future__ import annotations

from bootstrap import app
import curiosity_search as curiosity_search_module
from url_media_ingest import install as install_url_media_ingest

# Hard-coded product capability: public URL ingestion and best-effort YouTube
# transcript retrieval are part of the application runtime, not an optional
# text-patch step. install() is idempotent.
install_url_media_ingest(app, curiosity_search_module)

# Explicit marker for diagnostics/tests without exposing private state.
app.state.janus_url_media_ingestion_hardcoded = True
