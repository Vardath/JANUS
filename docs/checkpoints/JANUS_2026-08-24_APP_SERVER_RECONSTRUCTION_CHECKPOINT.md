# JANUS reconstruction checkpoint — 2026-08-24

## Status

This checkpoint records the clean reconstruction baseline after abandoning the broken legacy Android client lineage and the accumulated legacy server wrapper/patch chain.

## Product architecture

JANUS remains an experimental functional-metacognition/agency system. No claim of phenomenal consciousness is made.

The intended topology is present on both device and server:

**7 specialist cores → 2 hemisphere cores → Consensus → Interface**

Total: **11 cores**.

The device and server are separate JANUS societies with the same topology, not duplicate state stores.

- Device JANUS: lightweight local 11-core runtime, device-specific continuity, cheap/local background cycles, local responsiveness and offline queueing.
- Server JANUS: persistent global 11-core runtime, durable memory, research, account continuity, heavier synthesis and shared/global processing.
- Federation: selective, bounded, no-overwrite. Device material enters the server through specialist review; server guidance returns to the device and re-enters its specialists. Neither side directly overwrites the other's protected identity/core state.

## Android baseline

The old Android client is considered broken and is not a compatibility target.

Current clean native Android baseline is the v0.82 full rebuild under the authoritative `android/` application using package `com.vardath.janus`.

Important client requirements retained:

- Native UI; no legacy WebView product shell.
- Chat, Messages, Observe and Options navigation.
- Account/login/create/reset/verification/sign-out/account deletion surfaces.
- Runtime Cores, Memory, Activity, System Status, Compatibility, Research Workspace, Artifacts, Background Research, Maintenance, Settings and Account screens.
- Attachments and file grounding.
- Offline-safe queued chat with stable client message IDs.
- Generated-image display.
- Local 11-core runtime and selective server federation.
- Client local state can start clean; durable JANUS account/server continuity is restored only through authenticated server state.

## Clean server reconstruction

Production server reconstruction is `server_v2` and is intended to replace the old composed server rather than patch it.

The clean server must not depend on the legacy application composition/wrapper chain. Legacy code may serve as historical reference only; durable data can be migrated as data, not executable implementation.

Server requirements retained:

- Fresh account authentication and account isolation.
- Protected identity core.
- Per-account private state for all 11 server cores.
- Persistent core checkpoints/restoration.
- Exact foreground route: evidence, logic, counterpoint, context, memory, safety, novelty → left/right hemispheres → consensus → interface.
- Fano/JANUS specialist indexing is a processing bias/index, never a truth oracle.
- Adaptive bridge authority is learned but bounded so no evaluator becomes absolute.
- Reliability means historical calibration/consistency, not objective truth.
- Trace → working → episodic → core memory ladder.
- Selective-no-overwrite local/global federation.
- Chat idempotency and offline-safe client message IDs.
- Messages and proactive message candidates.
- Observe/activity for all 11 cores.
- Files, document grounding, image analysis and visual memory.
- Foreground web research, YouTube transcript research, provenance and Research Workspace.
- Artifacts/export.
- Explicit image generation plus rare explanatory images; medium quality by default.
- No autonomous multi-core background image generation.
- Cost governor and cheap-to-expensive model escalation.
- Background wake/sleep cognition with ordinary cycles making zero external model/API calls.
- Approximate intended cadence: 5 minutes wake / 10 minutes sleep in a 15-minute cycle.
- Owner-gated maintenance and quarterly maintenance review/email request; maintenance cannot autonomously deploy/edit/install/change providers.

## Model policy

Foreground model use follows deterministic preflight/escalation rather than always using the strongest model:

- GPT-5.6 Luna for inexpensive ordinary turns.
- GPT-5.6 Terra for intermediate complexity.
- GPT-5.6 Sol for higher-complexity/escalated work.

Preflight considers novelty, uncertainty, conflict, salience, evidence/research requirements and relevant memory.

## Live verification achieved

Structural/live tests established the following during this checkpoint:

- Clean v2 server reachable and reports `7->2->1->1`, 11 cores.
- Account registration/session authentication works in live smoke testing.
- Selective federation reports `selective-no-overwrite` and keeps local/global memory distinct.
- Chat requests traverse all seven specialists, both hemispheres, Consensus and Interface.
- File upload and specialist grounding work.
- Observe can expose all 11 cores.
- Persistent/private runtime, research workspace, artifacts, maintenance and account isolation are part of the structural integration gate.
- OpenAI provider initially failed because API credit balance was exhausted, not because of JANUS routing or model identity.
- After API credit was added, a direct live provider/JANUS chat diagnostic succeeded and produced a normal response through the full 11-core route with Luna selected for a simple greeting.

## Operational rule going forward

Do not return to the old Android patch chain or the old server wrapper composition.

Treat the clean native Android client and clean `server_v2` implementation as the development baselines. Preserve the architecture and feature plan above. Fix defects in these clean implementations rather than resurrecting legacy product code.

Compilation alone is not acceptance. Release/cutover confidence requires structural integration tests plus real-device/live-provider validation.

## Immediate follow-up

Continue live smoke validation of provider-dependent features after API credit restoration: ordinary chat, foreground web research, image generation, file/vision grounding and the full 11-core route. Investigate any transient 502s separately from provider/model failures. Keep production/client compatibility intact while fixing clean-server defects.
