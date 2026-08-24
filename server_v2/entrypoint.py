"""Production entrypoint for the clean JANUS server reconstruction.

No legacy application modules are imported here. Persisted account/memory records
are migrated as data only, then all runtime composition is provided by server_v2.
"""
from . import governance, identity, storage, visual_memory
from .migrate import migrate_persistent_data_once
from .runtime_persistence import runtime_persistence

storage.init_schema()
governance.init_schema()
identity.init_schema()
visual_memory.init_schema()
runtime_persistence.init_schema()
MIGRATION_RESULT = migrate_persistent_data_once()
RUNTIME_RESTORE_RESULT = runtime_persistence.restore_all()

from .app import app  # noqa: E402
from .advanced import router as advanced_router  # noqa: E402
from .background import background  # noqa: E402
from .chat import router as chat_router  # noqa: E402
from .identity_api import router as identity_router  # noqa: E402
from .sync_contract import router as sync_router  # noqa: E402

# Route ownership is explicit. Provisional routes in app.py are removed and each
# final reconstructed subsystem owns its endpoint exactly once.
_FINAL_REPLACEMENTS = {("/core-sync/exchange","POST"), ("/desktop/chat","POST")}
app.router.routes[:] = [
    route for route in app.router.routes
    if not any(getattr(route,"path",None)==path and method in getattr(route,"methods",set()) for path,method in _FINAL_REPLACEMENTS)
]
app.include_router(chat_router)
app.include_router(sync_router)
app.include_router(identity_router)
app.include_router(advanced_router)
app.add_event_handler("startup", background.start)
app.add_event_handler("startup", runtime_persistence.start)
app.add_event_handler("shutdown", runtime_persistence.stop)
app.add_event_handler("shutdown", background.stop)

app.state.server_generation = "v2-clean-reconstruction"
app.state.persistence_migration = MIGRATION_RESULT
app.state.runtime_restore = RUNTIME_RESTORE_RESULT
app.state.legacy_application_modules_loaded = False
app.state.background_multi_core_image_generation_enabled = False
