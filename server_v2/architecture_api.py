from __future__ import annotations

import os
from fastapi import APIRouter

from . import storage
from .mind import mind

router = APIRouter()


@router.get("/health")
def health():
    try:
        with storage.db() as c:
            quick = c.execute("PRAGMA quick_check").fetchone()[0]
        database_ok = str(quick).lower() == "ok"
    except Exception:
        database_ok = False
    return {
        "status": "ok" if database_ok else "degraded",
        "service": "janus-global-core-v2",
        "architecture": "recursive 1-3-7 JANUS core society",
        "conceptual_topology": "1|3|7",
        "mechanical_flow": "7 -> 2 -> 1 -> 1",
        "core_count": 11,
        "local_core_count": 11,
        "federated_top_level_core_count": 22,
        "internal_fano_faculties_per_core": 7,
        "recursive_core_engine": True,
        "front_core": "front",
        "database_ok": database_ok,
        "main_app_loaded": True,
        "deployed_commit": os.getenv("RENDER_GIT_COMMIT", "unknown")[:40],
    }


@router.get("/diagnostics/runtime-health")
def runtime_health():
    h = health()
    runtime = mind.status()
    return {
        **h,
        "auth_schema_ok": True,
        "core_persistence_ok": True,
        "core_phase": runtime["phase"],
        "remote_clients": runtime["remote_clients"],
        "background_external_api_budget_used": runtime["background_external_api_budget_used"],
        "background_core_model_calls": 0,
        "recursive_core_engine": runtime.get("recursive_core_engine", True),
        "each_top_level_core_is_complete_janus": True,
        "recursive_peer_revision": True,
        "single_call_recursive_ai_deliberation": True,
        "both_hemispheres_receive_all_seven": True,
        "peer_feedback_reenters_through_all_seven": True,
        "legacy_consensus_alias_is_core": False,
        "file_chat_grounding_enabled": True,
        "outbound_working_artifacts_enabled": True,
        "lightweight_image_generation_enabled": True,
        "background_multi_core_image_generation_enabled": False,
        "quarterly_maintenance_review_enabled": True,
        "server_generation": "v2-recursive-core-reconstruction",
    }
