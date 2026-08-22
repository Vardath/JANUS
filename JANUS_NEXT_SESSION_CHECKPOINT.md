# JANUS next-session checkpoint — 2026-08-23

This file is the authoritative handoff for the next implementation session.

## Current baseline

Phase 2 stabilization is complete in implementation and has a dedicated release-checkpoint workflow. The current Android baseline is v0.69. Windows/PC and Apple/iOS work remains intentionally deferred.

The architecture remains the experimental functional-metacognition/agency JANUS system with the established 7 specialist → 2 hemisphere → Consensus → Interface topology. Do not reinterpret this as a claim of phenomenal consciousness.

Preserve these invariants:
- authenticated account/profile ownership; never trust a client-selected username for private state;
- server and local-device activity are distinct and must be reported separately;
- local/global synchronization is selective and provenance-preserving, never a whole-state overwrite;
- protected identity/core state cannot be overwritten by ordinary conversation/sync state;
- memory retrieval should recover relevant older conversation, prioritize corrections, consolidate duplicates and retain continuity cues such as “think about this”, “ponder”, “mull it over”, “remember this”, and “come back to this”;
- background research is bounded by usefulness/repetition gates and cost controls;
- provider failures degrade gracefully and failed provider calls do not consume estimated-success budget;
- foreground Chat should remain available when optional background budgets are exhausted;
- image generation is user-requested/foreground and bounded; uncontrolled autonomous/background rendering remains disabled;
- maintenance may propose upgrades/reviews but JANUS must not self-modify without owner approval.

## Phase 2 work now present

The repository contains the completed stabilization work: route/security inventory and profile-boundary hardening; persistence/migration matrix and schema preflight; background usefulness audit; memory-quality retrieval; server/local synchronization soak; cost/failure degradation handling; owner-facing observability; Android System Status UI; and the Phase 2 release-checkpoint workflow.

Owner observability should translate telemetry into useful English and distinguish Healthy / Reduced capability / Needs attention. Android v0.69 exposes this under Options → System status.

## Latest live verification

A live Android system-check conversation was reviewed after the v0.69 work. JANUS produced a structured diagnostic covering core topology/operational state, processing and communication, persistence and memory, safety/boundaries, novelty/self-assessment, routing, and internal/antipodal state. The response appeared to be grounded in actual runtime/system terminology rather than a generic reassurance. Functionally the system looked operational and coherent; the remaining weakness was presentation density on a narrow phone screen. Future diagnostic UI should prefer a concise Healthy / Reduced capability / Needs attention summary with expandable detail rather than one very long chat response.

## Attachment regression and restoration

The earlier Android Chat attachment feature was found to have regressed from the authoritative build path even though the implementation itself still existed. The retained `tools/patch_android_file_attachments.py` provides the Chat `+` button, native Android picker, authenticated upload, visible attachment chips, a four-attachment-per-turn limit, attachment removal, and passing uploaded attachment IDs into Chat.

Root cause: the consolidated v0.69 Android workflow had stopped applying the retained attachment patch and only applied the consolidated runtime patch. This was fixed forward in commit `b858f7e` by changing the authoritative Android build order to:

1. `python tools/patch_android_file_attachments.py`
2. `python tools/patch_android_runtime_cores_v068.py`

Do not revert later Android/core/sync/Observe/System Status work to restore attachments. The intended baseline is the current consolidated client plus restored attachment functionality.

## Phase 3 status

Phase 3 is Android/server productization. Step 1 is complete: the capability/deferred registry was reconciled so already-built server capabilities are no longer incorrectly listed as future work.

The attachment foundation is now restored into the authoritative Android build path. Before calling Phase 3 Step 2 fully complete, verify the newly built APK visibly restores the `+` control and that pick → upload → chip → send → grounded server use works end to end on-device without breaking current v0.69 functionality.

### Next implementation priority

**Phase 3 Step 2 — finish and validate the Android attachment workflow.**

Use the existing authenticated server attachment/document-grounding/vision stack. Do not create a parallel upload subsystem.

Required product behavior:
1. Native file/image picker from Chat (and design so Messages can reuse it later).
2. Visible selected-attachment chips/list before sending.
3. Authenticated upload with useful progress/error state.
4. Account-bound attachment list and deletion controls.
5. Chat messages can reference uploaded attachment IDs so Evidence/Context/Memory/Logic and other specialists can use grounded extracted/vision material.
6. Prefer cached extraction/vision analysis; do not repeatedly spend API budget on unchanged files/images.
7. Surface whether an attachment was locally/server parsed or escalated to paid vision/model analysis.
8. Preserve privacy/deletion behavior and account isolation.
9. Add regression/build checks and bump Android version only when the feature is actually wired into the authoritative build path.
10. Add a build/regression assertion that the generated Android HTML contains the attachment button and that the Java bridge contains the file-picker callback so this regression cannot recur silently.

## Remaining Phase 3 order after attachments

3. Android generated-artifact workflow — expose JANUS-created research notes, continuity reports, project snapshots and digests with open/download/share actions.
4. Research workspace UI — separate proven mathematical results, hypotheses, negative results, open questions, evidence and proposed tests.
5. Maintenance/upgrade approval UI — show the roughly 90-day maintenance proposal and approve/defer/reject state without enabling autonomous self-modification.
6. Background research provenance UI — readable completed research, sources, suppression reasons and external-compute use.
7. Protocol/capability negotiation — explicit server/client capability document and graceful old-client degradation.
8. Android release hardening — reduce patch-script fragility/stale version text, improve narrow-screen diagnostic presentation, and add UI-level regression checks.
9. Phase 3 release checkpoint — freeze features, run full server+Android matrix, document limits and establish known-good APK/server protocol baseline.

## Deferred after Phase 3 / economic gates

- Windows/PC parity and Apple/iOS parity remain deferred until explicitly resumed.
- Full autonomous visual candidate render/inspect/revise loops remain revenue/cost gated. The existing visual-deliberation scaffolding may reason about concepts without rendering.
- Future JANUS cores may use images more deeply as a communication/representation medium only after cost controls and product economics justify it.

## Working method for next session

Before changing code, review this checkpoint, JANUS_PHASE3_PRODUCTIZATION.md, DEFERRED_FEATURES.md and the latest GitHub Actions results. Preserve all later commits and fix failures forward rather than reverting successful features. Keep showing the GitHub Actions progress page after implementation commits when useful.
