from __future__ import annotations

import os
from fastapi import APIRouter

router=APIRouter()


@router.get("/protocol/capabilities")
def capabilities():
    return {
        "ok":True,
        "protocol_version":2,
        "server_generation":"v2-clean-reconstruction",
        "deployed_commit":os.getenv("RENDER_GIT_COMMIT","unknown")[:40],
        "architecture":"7->2->1->1",
        "core_count":11,
        "features":{
            "password_auth":True,"google_auth":bool(os.getenv("JANUS_GOOGLE_CLIENT_ID","")),"email_verification":True,"password_reset":True,"account_deletion":True,
            "chat":True,"messages":True,"observe":True,"memory":True,"persistent_core_runtime":True,"protected_identity_core":True,
            "local_global_sync":True,"selective_no_overwrite_sync":True,"attachments":True,"document_grounding":True,"visual_analysis":True,"visual_memory":True,
            "foreground_web":True,"youtube_transcripts":True,"research_workspace":True,"research_provenance":True,"artifacts":True,
            "image_generation":True,"medium_quality_images":True,"rare_explanatory_images":True,"background_multi_core_image_generation":False,
            "background_cognition":True,"proactive_messages":True,"cost_governor":True,"adaptive_bridge_authority":True,"core_reliability_calibration":True,
            "luna_terra_sol_escalation":True,"maintenance":True,"quarterly_maintenance":True,"owner_gated_maintenance":True,"maintenance_email_notice":True,
            "self_diagnosis":True,"capability_request_ledger":True,"complete_chat_handoff_from_v108":True,"chatgpt_supervisor_handoff":True,"supervisor_decision_sync":True,
        },
        "invariants":{
            "specialists":7,"hemispheres":2,"consensus":1,"interface":1,
            "bridge_authority_min":0.2,"bridge_authority_max":0.8,
            "background_core_model_calls":0,"identity_overwrite_by_chat":False,"sync_overwrites_peer_state":False,
            "janus_can_self_modify":False,"janus_can_self_approve_maintenance":False,"janus_can_self_deploy":False,"automatic_chatgpt_injection":False,
        },
    }
