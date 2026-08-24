"""Production entrypoint for the clean JANUS server reconstruction.

No legacy application modules are imported here. Persisted account/memory records
are migrated as data only, then all runtime composition is provided by server_v2.
"""
from . import governance, storage
from .migrate import migrate_persistent_data_once

storage.init_schema()
governance.init_schema()
MIGRATION_RESULT = migrate_persistent_data_once()

from .app import app  # noqa: E402
from .advanced import router as advanced_router  # noqa: E402
from .background import background  # noqa: E402
from .sync_contract import router as sync_router  # noqa: E402

# Route ownership is explicit in the reconstructed server. Replace the temporary
# sync endpoint defined in app.py with the final native-client federation contract.
app.router.routes[:] = [
    route for route in app.router.routes
    if not (getattr(route, "path", None) == "/core-sync/exchange" and "POST" in getattr(route, "methods", set()))
]
app.include_router(sync_router)
app.include_router(advanced_router)
app.add_event_handler("startup", background.start)
app.add_event_handler("shutdown", background.stop)

app.state.server_generation = "v2-clean-reconstruction"
app.state.persistence_migration = MIGRATION_RESULT
app.state.legacy_application_modules_loaded = False
app.state.background_multi_core_image_generation_enabled = False
