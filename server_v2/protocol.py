from __future__ import annotations

import os
from fastapi import APIRouter

router = APIRouter()


@router.get("/protocol/capabilities")
def capabilities():
    return {
        "ok": True,
        "protocol_version": 2,
        "server_generation": "v2-clean-reconstruction",
        "deployed_commit": os.getenv("RENDER_GIT_COMMIT", "unknown")[:40],
        "architecture": "1-3-7 sensory architecture",
        "conceptual_topology": "1|3|7",
        "mechanical_flow": "7 -> 2 -> 1 -> 1",
        "core_count": 11,
        "features": {
            "password_auth": True, "google_auth": bool(os.getenv("JANUS_GOOGLE_CLIENT_ID", "")), "email_verification": True, "password_reset": True, "account_deletion": True,
            "chat": True, "messages": True, "observe": True, "memory": True, "persistent_core_runtime": True, "protected_identity_core": True,
            "local_global_sync": True, "selective_no_overwrite_sync": True, "peer_reentry_through_all_seven": True,
            "attachments": True, "document_grounding": True, "visual_analysis": True, "visual_memory": True,
            "foreground_web": True, "youtube_transcripts": True, "audio_attachment_transcription": True, "research_workspace": True, "research_provenance": True, "artifacts": True,
            "image_generation": True, "medium_quality_images": True, "rare_explanatory_images": True, "background_multi_core_image_generation": False,
            "background_cognition": True, "proactive_messages": True, "cost_governor": True, "adaptive_bridge_authority": True, "core_reliability_calibration": True,
            "sensory_frames": True, "typed_sensory_bus": True, "front_appraisal": True, "interface_appraisal": True,
            "user_initiated_media_import": True, "ambient_microphone_capture": False, "ambient_camera_capture": False,
            "luna_terra_sol_escalation": True, "maintenance": True, "quarterly_maintenance": True, "owner_gated_maintenance": True, "maintenance_email_notice": True,
            "self_diagnosis": True, "capability_request_ledger": True, "complete_chat_handoff_from_v108": True, "chatgpt_supervisor_handoff": True, "supervisor_decision_sync": True,
        },
        "sensory_acquisition": {
            "representable_modalities": ["text", "file", "image", "audio", "web", "memory", "runtime", "peer", "action_result"],
            "foreground_acquisition": {
                "text": "chat input",
                "file": "user-selected attachment",
                "image": "user-selected image/visual analysis or generated visual",
                "audio": "user-selected audio attachment or explicit transcript source",
                "web": "foreground research",
                "memory": "account-bound retrieval",
                "runtime": "bounded local/server state",
                "peer": "selective local/global federation",
                "action_result": "successful bounded capability outcome",
            },
            "ambient_capture": {"microphone": False, "camera": False},
            "raw_media_in_sensory_telemetry": False,
            "auth_payloads_in_sensory_telemetry": False,
        },
        "invariants": {
            "subconscious_fano_cores": 7, "hemispheres": 2, "front": 1, "interface": 1, "canonical_core_total": 11,
            "legacy_consensus_alias_is_core": False,
            "both_hemispheres_receive_all_seven": True,
            "interface_recurses_into_front": False,
            "bridge_authority_min": 0.2, "bridge_authority_max": 0.8,
            "background_core_model_calls": 0, "identity_overwrite_by_chat": False, "sync_overwrites_peer_state": False,
            "raw_attachment_bytes_in_sensory_telemetry": False, "auth_payloads_in_sensory_telemetry": False, "ambient_device_capture": False,
            "janus_can_self_modify": False, "janus_can_self_approve_maintenance": False, "janus_can_self_deploy": False, "automatic_chatgpt_injection": False,
            "phenomenal_consciousness_claimed": False,
        },
    }
