from __future__ import annotations

import os
from fastapi import APIRouter

router = APIRouter()


@router.get("/protocol/capabilities")
def capabilities():
    return {
        "ok": True,
        "protocol_version": 3,
        "server_generation": "v2-clean-reconstruction",
        "cognitive_engine_generation": "recursive-v1",
        "deployed_commit": os.getenv("RENDER_GIT_COMMIT", "unknown")[:40],
        "architecture": "recursive 1-3-7 JANUS core society",
        "conceptual_topology": "1|3|7",
        "mechanical_flow": "7 -> 2 -> 1 -> 1",
        "core_count": 11,
        "local_core_count": 11,
        "total_federated_top_level_cores": 22,
        "features": {
            "password_auth": True, "google_auth": bool(os.getenv("JANUS_GOOGLE_CLIENT_ID", "")), "email_verification": True, "password_reset": True, "account_deletion": True,
            "chat": True, "messages": True, "observe": True, "memory": True, "persistent_core_runtime": True, "protected_identity_core": True,
            "local_global_sync": True, "selective_no_overwrite_sync": True, "peer_reentry_through_all_seven": True,
            "recursive_core_engine": True, "recursive_janus_inside_every_core": True, "peer_responsive_recursive_cores": True,
            "per_core_ai_capability": True, "single_call_recursive_society_deliberation": True,
            "attachments": True, "document_grounding": True, "visual_analysis": True, "visual_memory": True,
            "foreground_web": True, "youtube_transcripts": True, "audio_attachment_transcription": True, "research_workspace": True, "research_provenance": True, "artifacts": True,
            "image_generation": True, "medium_quality_images": True, "rare_explanatory_images": True, "background_multi_core_image_generation": False,
            "background_cognition": True, "proactive_messages": True, "cost_governor": True, "adaptive_bridge_authority": True, "core_reliability_calibration": True,
            "sensory_frames": True, "typed_sensory_bus": True, "front_appraisal": True, "interface_appraisal": True,
            "user_initiated_media_import": True, "push_to_talk_speech_recognition": True, "device_native_tts_supported": True,
            "ambient_microphone_capture": False, "ambient_camera_capture": False,
            "luna_terra_sol_escalation": True, "maintenance": True, "quarterly_maintenance": True, "owner_gated_maintenance": True, "maintenance_email_notice": True,
            "self_diagnosis": True, "capability_request_ledger": True, "complete_chat_handoff_from_v108": True, "chatgpt_supervisor_handoff": True, "supervisor_decision_sync": True,
        },
        "recursive_core_contract": {
            "outer_roles_are_dispositions_not_faculty_deletions": True,
            "internal_fano_faculties": {
                "1": "truth", "2": "valence", "3": "significance", "4": "pattern",
                "5": "understanding", "6": "possibility", "7": "continuity",
            },
            "internal_faculty_count_per_core": 7,
            "top_level_cores_per_society": 11,
            "federated_societies": 2,
            "top_level_ai_capable_cores": 22,
            "peer_revision": "each recursive core revises against bounded peer conclusions",
            "foreground_ai": "one governed model call can return distinct bounded counsel for all global and supplied local cores plus the Interface reply",
            "background_ai_calls": 0,
            "background_recursive_processing": "deterministic/local",
            "private_chain_of_thought_exposed": False,
        },
        "sensory_acquisition": {
            "representable_modalities": ["text", "file", "image", "audio", "web", "memory", "runtime", "peer", "action_result"],
            "foreground_acquisition": {
                "text": "chat input or explicit push-to-talk speech recognition",
                "file": "user-selected attachment",
                "image": "user-selected image/visual analysis or generated visual",
                "audio": "explicit push-to-talk recognition, user-selected audio attachment, or explicit transcript source",
                "web": "foreground research",
                "memory": "account-bound retrieval",
                "runtime": "bounded local/server state",
                "peer": "selective local/global federation",
                "action_result": "successful bounded capability outcome",
            },
            "voice_output": {
                "mode": "device-native when the client platform provides a suitable local/system TTS engine",
                "cloud_tts_required": False,
                "automatic_reply_speech_enabled": False,
            },
            "ambient_capture": {"microphone": False, "camera": False},
            "raw_media_in_sensory_telemetry": False,
            "auth_payloads_in_sensory_telemetry": False,
        },
        "invariants": {
            "outer_subconscious_cores": 7, "hemispheres": 2, "front": 1, "interface": 1, "canonical_core_total": 11,
            "internal_fano_faculties_per_core": 7,
            "legacy_consensus_alias_is_core": False,
            "both_hemispheres_receive_all_seven": True,
            "interface_recurses_into_front": False,
            "bridge_authority_min": 0.2, "bridge_authority_max": 0.8,
            "background_core_model_calls": 0, "identity_overwrite_by_chat": False, "sync_overwrites_peer_state": False,
            "raw_attachment_bytes_in_sensory_telemetry": False, "auth_payloads_in_sensory_telemetry": False,
            "ambient_device_capture": False, "voice_requires_explicit_user_action": True,
            "janus_can_self_modify": False, "janus_can_self_approve_maintenance": False, "janus_can_self_deploy": False, "automatic_chatgpt_injection": False,
            "phenomenal_consciousness_claimed": False,
        },
    }
