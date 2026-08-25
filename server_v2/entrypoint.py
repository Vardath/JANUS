"""Production entrypoint for the clean recursive JANUS server.

Persisted account/memory records are migrated as data only. Runtime composition uses
one RecursiveJanusMind instance so Chat, sensing, sync, diagnostics, persistence and
background coordination cannot accidentally split between different societies.
"""
from . import diagnostics, governance, identity, storage, visual_memory
from . import mind as base_mind_module
from . import runtime_persistence as runtime_persistence_module
from .maintenance_seed import apply_pending_seed
from .migrate import migrate_persistent_data_once
from .recursive_mind import mind as recursive_mind
from .runtime_persistence import runtime_persistence

# Every subsystem, including compatibility imports of server_v2.mind.mind, must refer
# to the same recursive production society rather than creating split cognitive state.
base_mind_module.mind = recursive_mind
runtime_persistence_module.mind = recursive_mind

# Preserve the historical per-turn reply override used by offline verification and
# diagnostic harnesses. Normal production has no instance-level _model_reply override,
# so it continues through the single governed recursive society model call.
_recursive_deliberation = recursive_mind._model_deliberation
def _compatible_recursive_deliberation(account_id, message, global_states, local_states, memories, evidence, web_context, selected_model):
    override = recursive_mind.__dict__.get("_model_reply")
    if callable(override):
        try:
            reply = override(account_id, message, {"summary": "recursive verification override"}, memories, evidence, web_context, selected_model)
            return str(reply), {}, {}
        except Exception:
            pass
    return _recursive_deliberation(account_id, message, global_states, local_states, memories, evidence, web_context, selected_model)
recursive_mind._model_deliberation = _compatible_recursive_deliberation

storage.init_schema()
governance.init_schema()
identity.init_schema()
visual_memory.init_schema()
diagnostics.init_schema()
runtime_persistence.init_schema()
MIGRATION_RESULT = migrate_persistent_data_once()
MAINTENANCE_SEED_RESULT = apply_pending_seed()
RUNTIME_RESTORE_RESULT = runtime_persistence.restore_all()
SUPERVISOR_DECISION_SYNC = diagnostics.apply_supervisor_decisions()

# Import final subsystems as modules so their historical `mind` globals can all be
# rebound to the one recursive production mind before the routers handle requests.
from . import architecture_api as architecture_module  # noqa: E402
from . import background as background_module  # noqa: E402
from . import chat as chat_module  # noqa: E402
from . import desktop as desktop_module  # noqa: E402
from . import sensory_bus as sensory_bus_module  # noqa: E402
from . import sync_contract as sync_module  # noqa: E402
from . import recursive_sensory  # noqa: E402

architecture_module.mind = recursive_mind
background_module.mind = recursive_mind
chat_module.mind = recursive_mind
desktop_module.mind = recursive_mind
sync_module.mind = recursive_mind
sensory_bus_module.mind = recursive_mind
# All capability/file/image/audio/web/action senses now use recursive cognition too.
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
from .sync_contract import router as sync_router  # noqa: E402

# Route ownership is explicit. Provisional routes in app.py are removed and each
# final reconstructed subsystem owns its endpoint exactly once.
_FINAL_REPLACEMENTS = {
    ("/health","GET"), ("/diagnostics/runtime-health","GET"),
    ("/core-sync/exchange","POST"), ("/desktop/chat","POST"),
    ("/desktop/runtime-cores","GET"), ("/desktop/cores","GET"), ("/desktop/memory","GET"),
    ("/desktop/activity","GET"), ("/desktop/core-observe","GET"), ("/desktop/observe","GET"),
    ("/desktop/home","GET"), ("/desktop/settings","GET"),
    ("/protocol/capabilities","GET"),
    ("/images/generate","POST"), ("/images/usage","GET"),
    ("/maintenance/status","GET"), ("/maintenance/reviews/{review_id}/decision","POST"),
}
app.router.routes[:] = [
    route for route in app.router.routes
    if not any(getattr(route,"path",None)==path and method in getattr(route,"methods",set()) for path,method in _FINAL_REPLACEMENTS)
]
app.include_router(architecture_router)
app.include_router(chat_router)
app.include_router(sync_router)
app.include_router(desktop_router)
app.include_router(protocol_router)
app.include_router(provider_router)
app.include_router(image_router)
app.include_router(maintenance_router)
app.include_router(identity_router)
app.include_router(advanced_router)
app.add_event_handler("startup", background.start)
app.add_event_handler("startup", runtime_persistence.start)
app.add_event_handler("startup", recursive_mind.start)
app.add_event_handler("shutdown", recursive_mind.stop)
app.add_event_handler("shutdown", runtime_persistence.stop)
app.add_event_handler("shutdown", background.stop)

app.state.server_generation = "v2-clean-reconstruction"
app.state.cognitive_engine_generation = "recursive-v1"
app.state.persistence_migration = MIGRATION_RESULT
app.state.maintenance_seed = MAINTENANCE_SEED_RESULT
app.state.runtime_restore = RUNTIME_RESTORE_RESULT
app.state.supervisor_decision_sync = SUPERVISOR_DECISION_SYNC
app.state.legacy_application_modules_loaded = False
app.state.background_multi_core_image_generation_enabled = False
app.state.recursive_core_engine = True
app.state.recursive_core_count = 11
app.state.local_recursive_core_count = 11
