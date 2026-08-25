"""Production entrypoint for the recursive JANUS conscious-stream server."""
from . import diagnostics, governance, identity, storage, visual_memory
from . import mind as base_mind_module
from . import runtime_persistence as runtime_persistence_module
from .maintenance_seed import apply_pending_seed
from .migrate import migrate_persistent_data_once
from .conscious_mind import mind as recursive_mind
from .runtime_persistence import runtime_persistence

base_mind_module.mind = recursive_mind
runtime_persistence_module.mind = recursive_mind

storage.init_schema(); governance.init_schema(); identity.init_schema(); visual_memory.init_schema(); diagnostics.init_schema(); runtime_persistence.init_schema()
MIGRATION_RESULT = migrate_persistent_data_once()
MAINTENANCE_SEED_RESULT = apply_pending_seed()
RUNTIME_RESTORE_RESULT = runtime_persistence.restore_all()
SUPERVISOR_DECISION_SYNC = diagnostics.apply_supervisor_decisions()

from . import architecture_api as architecture_module  # noqa: E402
from . import background as background_module  # noqa: E402
from . import chat as chat_module  # noqa: E402
from . import desktop as desktop_module  # noqa: E402
from . import sensory_bus as sensory_bus_module  # noqa: E402
from . import sync_contract as sync_module  # noqa: E402
from . import recursive_sensory  # noqa: E402
architecture_module.mind=recursive_mind; background_module.mind=recursive_mind; chat_module.mind=recursive_mind; desktop_module.mind=recursive_mind; sync_module.mind=recursive_mind; sensory_bus_module.mind=recursive_mind
sensory_bus_module.ingest = recursive_sensory.ingest

from .app import app  # noqa: E402
from .advanced import router as advanced_router  # noqa: E402
from .architecture_api import router as architecture_router  # noqa: E402
from .background import background  # noqa: E402
from .chat import router as chat_router  # noqa: E402
from .desktop import router as desktop_router  # noqa: E402
from .identity_api import router as identity_router  # noqa: E402
from .images import router as image_router  # noqa: E402
from .maintenance import router as maintenance_router  # noqa: E402
from .protocol import router as protocol_router  # noqa: E402
from .provider_diagnostics import router as provider_router  # noqa: E402
from .stream_api import router as stream_router  # noqa: E402
from .sync_contract import router as sync_router  # noqa: E402

_FINAL_REPLACEMENTS={("/health","GET"),("/diagnostics/runtime-health","GET"),("/core-sync/exchange","POST"),("/desktop/chat","POST"),("/desktop/runtime-cores","GET"),("/desktop/cores","GET"),("/desktop/memory","GET"),("/desktop/activity","GET"),("/desktop/core-observe","GET"),("/desktop/observe","GET"),("/desktop/stream-observe","GET"),("/desktop/home","GET"),("/desktop/settings","GET"),("/protocol/capabilities","GET"),("/images/generate","POST"),("/images/usage","GET"),("/maintenance/status","GET"),("/maintenance/reviews/{review_id}/decision","POST")}
app.router.routes[:]=[route for route in app.router.routes if not any(getattr(route,"path",None)==path and method in getattr(route,"methods",set()) for path,method in _FINAL_REPLACEMENTS)]
for router in (architecture_router,chat_router,sync_router,desktop_router,stream_router,protocol_router,provider_router,image_router,maintenance_router,identity_router,advanced_router): app.include_router(router)
app.add_event_handler("startup",background.start); app.add_event_handler("startup",runtime_persistence.start); app.add_event_handler("startup",recursive_mind.start)
app.add_event_handler("shutdown",recursive_mind.stop); app.add_event_handler("shutdown",runtime_persistence.stop); app.add_event_handler("shutdown",background.stop)

app.state.server_generation="v2-clean-reconstruction"
app.state.cognitive_engine_generation="recursive-conscious-stream-v2"
app.state.persistence_migration=MIGRATION_RESULT; app.state.maintenance_seed=MAINTENANCE_SEED_RESULT; app.state.runtime_restore=RUNTIME_RESTORE_RESULT; app.state.supervisor_decision_sync=SUPERVISOR_DECISION_SYNC
app.state.legacy_application_modules_loaded=False; app.state.background_multi_core_image_generation_enabled=False
app.state.recursive_core_engine=True; app.state.recursive_core_count=11; app.state.local_recursive_core_count=11
app.state.outward_route="7 specialists -> left/right -> front -> interface"
