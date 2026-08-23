# JANUS Phase 3 — Android/server productization

Phase 2 established the stabilization baseline. Phase 3 turns implemented server capabilities into coherent Android workflows.

## Scope boundary
- Android + server only.
- Preserve 7→2→1→1 architecture, authenticated ownership, selective sync/provenance, and no whole-state overwrite.
- Keep autonomous paid work bounded and background image rendering disabled.

## Ordered plan
1. Capability/deferred registry — **IMPLEMENTED.**
2. URL / YouTube / transcript research integration — **IMPLEMENTED 2026-08-23; deployment/regression validation pending.** Direct public URL text ingestion, per-video transcript attempts, provenance, profile-isolated caching, no-fabrication fallback and truthful capability reporting.
3. Android attachment workflow — **IMPLEMENTED; regression/productization CI added, live end-to-end validation pending.** Native picker, account-bound upload, attachment chips, four-file turn limit and specialist grounding are preserved in the authoritative build chain.
4. Android generated-artifact workflow — **IMPLEMENTED IN CLIENT BUILD PATH; CI/live validation pending.** Android Options exposes account-bound continuity reports and research digests, lists existing JANUS artifacts, opens provenance/details, can attach generated artifact files back into Chat for grounded discussion, and exposes native Android Download/Export and Share controls.
5. Research workspace UI — **IMPLEMENTED IN CLIENT BUILD PATH; CI/live validation pending.** Android Options exposes the account-bound research workspace with separate filters for established/audited work, hypotheses/provisional work, retained negative results, open questions and proposed tests. Users can seed the JANUS baseline idempotently and hand a research item back to Chat with its epistemic status explicitly preserved.
6. Maintenance/upgrade approval UI — **IMPLEMENTED IN SERVER + CLIENT BUILD PATH; CI/live validation pending.** The configured owner can inspect quarterly maintenance proposals and record Approve-for-manual-work, Defer or Reject decisions. Approval is explicitly advisory/manual-only: it never lets JANUS modify code, install dependencies, switch models/APIs, alter configuration or deploy autonomously. Non-owner accounts are denied access.
7. Background research provenance UI — **IMPLEMENTED IN SERVER + CLIENT BUILD PATH; CI/live validation pending.** Android Options exposes account-scoped background research history, recorded sources, usefulness/suppression reasons, and the cost-governor's estimated external-compute usage. Suppressed candidates remain visible as evidence that JANUS chose not to spend budget. The screen does not expose private chain-of-thought and keeps background image generation disabled.
8. Protocol/capability negotiation — **IMPLEMENTED IN SERVER + CLIENT BUILD PATH; primary Android/build checks green.** The public `/protocol/capabilities` endpoint reports protocol compatibility, deployed commit identity, minimum/recommended Android client version, actual route-backed feature availability and protected safety boundaries. Android refreshes this capability map after sign-in and exposes a Compatibility screen; optional product buttons are disabled when the deployed server does not advertise the required feature rather than pretending support exists.
9. Android release/UI hardening — **IMPLEMENTED; FINAL CI/LIVE VALIDATION PENDING.** v0.70 client baseline, device-local system/light/dark themes, custom accent/user-message/surface colours, automatic readable contrast, native artifact Download/Export and Share, and UI composition regressions are implemented. The authoritative APK build and release checkpoint now use one `tools/compose_android_phase3.py` entrypoint. Historical patch modules remain as tested components, but workflows no longer duplicate the fragile ordered patch chain. The composer owns ordering and verifies required postconditions before Gradle runs.
10. Phase 3 release checkpoint.

## URL/media boundary
Foreground pasted URLs are fetched directly where public text is available. YouTube video URLs attempt captions/transcripts and retain an explicit unavailable state rather than fabricating text. Retrieved material is injected into the existing multi-core research fabric. Cache keys are profile + canonical URL. Channel-wide autonomous crawling remains disabled; bounded channel discovery continues through the existing web-search fabric.

## Research workspace boundary
The Android research screen is a view over the existing authenticated server research ledger; it does not create a second research database. The server remains authoritative for claim kinds and epistemic states. Negative and falsified branches remain visible. The UI must never imply that mathematical recurrence establishes a physical or cosmological claim. Evidence entries do not automatically promote a hypothesis.

## Maintenance approval boundary
Maintenance review remains owner-controlled and advisory. `approved_for_manual_work` means the owner has authorized a human/ChatGPT-assisted maintenance session; it is not permission for JANUS to self-edit, self-upgrade, self-deploy, install packages, change models/APIs or alter protected configuration. Defer and Reject likewise only record the owner's disposition. The owner-facing API is authenticated and restricted to `JANUS_MAINTENANCE_OWNER_PROFILE`.

## Background research provenance boundary
The provenance screen reports only externalizable records: search queries, source URLs/titles, usefulness-gate decisions and estimated external-compute accounting. It is account-scoped and must not imply access to private chain-of-thought. Cost values are budgeting estimates from JANUS's governor, not provider invoices. A suppressed candidate means JANUS deliberately declined optional background work before spending external budget; it is not a failed foreground request.

## Protocol negotiation boundary
Capability negotiation is intentionally public but contains only product compatibility facts: protocol versions, deploy identity, client-version guidance, route-backed feature booleans and safety-boundary flags. It exposes no account data, tokens, private diagnostics or reasoning. Clients must treat missing/unadvertised optional capabilities conservatively. Negotiation does not authorize whole-state overwrite, autonomous code changes, package installation, model/API switching or deployment.

## Interface theme controls
Theme controls belong to the client/productization layer, not JANUS cognition. v0.70 supports system/light/dark appearance, a custom accent colour, user-message colour and surface tint. Accent text contrast is selected automatically. Settings remain device-local and do not alter JANUS cognition, account state or server configuration. Subtle per-role specialist/hemisphere/consensus colours remain optional future polish rather than a requirement.

## Native artifact export boundary
Artifact export reuses the authenticated, account-bound `/files/{file_id}/download` route. Download/Export writes only to a user-selected Android document destination. Share first downloads to the app's private cache and exposes only that temporary file through a non-exported FileProvider with temporary read permission to the selected share target. Neither path makes JANUS files public on the server or weakens account ownership.

## Android composition boundary
`tools/compose_android_phase3.py` is now the authoritative product composition entrypoint used by the APK workflow and release checkpoint. It applies the tested feature modules in one declared order and verifies key UI/native/version markers after composition. This reduces workflow drift without deleting the individual patch modules, so regressions remain attributable and fixes can still be made forward without reverting newer features.
