# JANUS Phase 3 Release Checkpoint — Android/server v0.70

This checkpoint freezes the current Phase 3 Android/server product baseline before any further feature work.

## Release identity
- Android version: **0.70** (`versionCode 70`).
- Android package: `com.vardath.janus`.
- Authoritative Android composition entrypoint: `tools/compose_android_phase3.py`.
- Server remains the authenticated JANUS global core with selective sync and account-bound persistence.

## Frozen Phase 3 product surface
- 7→2→1→1 JANUS architecture preserved.
- Authenticated account ownership and selective federated sync preserved; no whole-state overwrite.
- URL / public-web ingestion with bounded YouTube transcript/caption attempts and explicit unavailable fallback.
- Native Android attachment picker/upload/chat grounding with specialist-core grounding.
- Account-bound generated artifacts with provenance, reuse in Chat, Download/Export and Android Share.
- Research Workspace UI with explicit epistemic categories and retained negative results.
- Owner-only quarterly maintenance review with Approve-for-manual-work / Defer / Reject; no autonomous self-modification or deployment.
- Background research provenance UI exposing externalizable sources, suppression decisions and estimated external-compute budget usage, not private chain-of-thought.
- Public protocol/capability negotiation with conservative client feature gating.
- Device-local System / Light / Dark themes plus custom accent, user-message and surface colours with contrast protection.
- Background multi-core image generation remains disabled.

## Release gates
The dedicated `Phase 3 Release Checkpoint` workflow must pass all of the following before this checkpoint is treated as release-valid:

1. Server security/architecture regression subset.
2. Phase 3 Android productization regression subset.
3. One clean run of `tools/compose_android_phase3.py`.
4. Verification of Android v0.70 identity and required composed UI/native markers.
5. A full Gradle debug APK build using the same composed source tree.
6. Upload of a release-candidate APK artifact plus a small build-identity manifest.

## Safety and truthfulness boundaries
- Missing URL/transcript material must be reported as unavailable; JANUS must not fabricate a transcript.
- Research evidence does not automatically promote hypotheses to established claims.
- Maintenance approval authorizes manual owner/ChatGPT-assisted work only.
- Capability negotiation exposes compatibility facts only, never account secrets or private reasoning.
- Artifact export/share never makes account files public on the JANUS server.
- Theme controls are client-local and never alter JANUS cognition.

## Freeze rule
Once the Phase 3 release checkpoint is green, treat this v0.70 Android/server baseline as known-good. Subsequent feature work should begin from a new phase/version or a clearly documented hotfix branch; do not silently mutate the frozen product surface.

## Deferred beyond this checkpoint
- Windows/PC parity.
- Apple/iOS parity.
- Autonomous background image rendering and recursive paid image critique loops.
- Optional specialist/hemisphere/consensus colour polish.
