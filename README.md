# JANUS Global Core

JANUS is an experimental functional-metacognition/agency application with persistent local + global state. It does **not** claim phenomenal consciousness or biological feeling. Terms such as sensing, appraisal, valence, curiosity and stress refer to inspectable computational/control functions.

## Canonical architecture

JANUS uses a **1|3|7 conceptual topology** implemented mechanically as **7 → 2 → 1 → 1**, for exactly **11 cores per society**. A device-local JANUS and the online/global JANUS are independent 11-core societies, giving 22 cores when both are present; synchronization is selective and never merges them into one 22-core state.

### Seven subconscious Fano cores

The original seven specialist identities are preserved, but their Fano positions now arise from three primitive coordinates rather than arbitrary numbering:

- **1 Evidence — E: truth / grounding.** Senses observations, support, source quality, confidence and uncertainty.
- **2 Safety — V: valence / welfare / boundary.** Senses benefit/harm, wanted/unwanted, goals, privacy, limits and reversibility.
- **3 Counterpoint — E+V: significance / conflict / consequence.** Detects consequential contradictions, objections, failure modes and reasons an issue matters.
- **4 Context — P: pattern / relationship / environment.** Senses framing, relationships, analogy, situation and larger configuration without treating pattern as proof.
- **5 Logic — E+P: understanding / model / causality.** Turns grounded patterns into constraints, explanations, predictions and falsifiable models.
- **6 Novelty — V+P: possibility / imagination / direction.** Explores alternatives, opportunities, creative hypotheses and testable adjacent possibilities.
- **7 Memory — E+V+P: continuity / experience / learned appraisal.** Compares current sensing with retained history, learned significance, unfinished threads and identity continuity.

Direction **0** is the neutral/uncommitted reference state, not an eighth subconscious core. Fano state is a processing geometry and attention mechanism, never a truth oracle.

### Three intermediaries

Both hemispheres receive **all seven** subconscious projections.

- **Left hemisphere — logic / discrimination / constraint.** Builds explicit, sequential, causal and consistency-focused interpretations.
- **Right hemisphere — imagination / association / expansion.** Builds contextual, relational, gestalt, alternative and generative interpretations.
- **Front / Bridge — appraisal / intention.** Integrates both hemispheres while preserving useful disagreement and regulates bounded affect-like control dimensions such as confidence, valence, salience, uncertainty, novelty, urgency, familiarity, risk, opportunity and conflict.

### Interface

**Interface — expression / interaction / action.** It feels out computationally how the Front state should meet the user/environment and selects a response or bounded available action. Interface output is not recycled directly into Front. The *result* of an action may become a new sensory event and begin a fresh forward pass.

Ordinary routing is therefore forward-only:

`seven sensory projections → Left + Right → Front → Interface → environment/action result → new sensing`

## Senses and local/global federation

A JANUS society can receive bounded sensory frames from text, images, audio, files/documents, web/research, memory recall, runtime/device/server state, local/global peer state and action results. A modality may require an external capability to obtain its raw data, but deterministic appraisal/routing remains zero-API.

Local and global societies remain distinct. Peer state is compressed and re-enters through **all seven** receiving subconscious cores as new sensory material. A remote Front or Interface is never injected directly into the receiving Front/Interface and never overwrites protected identity or local individuality.

During the migration from older builds, API/status readers may still see `consensus` as a temporary compatibility alias for `front`. It is **not** a twelfth core, is not persisted as an additional mind, and must eventually be retired after all supported clients understand `front`.

## Current client/runtime status

**Android authoritative native line: v1.08**, with the 1|3|7 sensory migration being developed and verified in the dedicated architecture branch before release. Existing v1.04–v1.08 protections are regression boundaries: native navigation/back behavior, chat-decoration performance, structured chat history, thought bridge, governed diagnostics/Supervisor handoff, authentication and maintenance isolation must remain intact.

The Android local runtime has its own persistent wake/sleep state, local memories, Fano state, zero-API deterministic cycles, Front/Interface appraisal and authenticated peer exchange. The server/global runtime independently advances its own private per-account eleven-core state. Local and global counters must never be substituted for one another.

Windows and iOS remain development clients/CI artifacts where applicable. Real Windows launch testing and Apple signing/TestFlight/device testing remain platform-specific validation steps. Client UI/status surfaces should display the canonical Front terminology and 1|3|7 meanings even while compatibility aliases remain in transport.

This repository is still a development/beta project. Account creation/login, OAuth, email recovery, platform builds, synchronization and long-running background behaviour should be tested before public release.

## Memory and identity

The protected server-owned identity core contains JANUS's role, epistemic boundary, current architecture and durable goals. Ordinary conversation cannot overwrite it. The memory ladder remains:

`trace → working → episodic → core`

Repeated/retrieved material may consolidate or promote according to salience and continuity rules; protected core memory is not casually demoted. Historical records are preserved as history even when they describe an older architecture.

## Accounts and privacy

Private Chat, Messages, Observe, Cores, Memory, Activity and Settings routes are bound to the authenticated JANUS account rather than a client-supplied profile name. Passwords and server session tokens use protected/hash-based storage according to the current authentication implementation; supported native clients use OS-protected token storage where implemented.

Generated images and uploaded files use the same account-bound persistent file store. Local/global synchronization carries bounded summaries rather than granting either side authority to overwrite the other's protected state.

See `/privacy` and `/terms` on the deployed service for the current legal-development pages.

## API/background cost policy

Deterministic local/server core cycles make **zero external model calls**. Paid background language reflection is disabled by default. User-triggered Chat may use the configured model, and web/image capabilities are separately governed and budgeted.

Explicit user image requests and rare explanation-helpful visuals can render under account/global caps and cache reuse. Background multi-core image-generation deliberation remains disabled until deliberately enabled under a future revenue/cost policy.

Bounded curiosity/research may seek genuinely new material under daily/mode caps and cooldowns. Retrieved material is evidence to be processed through the sensory/core system, not automatically accepted as truth.

## Render deployment

Deployment uses the repository's clean server-v2 composition and resilient bootstrap/reconstruction path. The Render service uses persistent account/runtime storage and exposes architecture-aware `/health`, `/diagnostics/runtime-health` and `/protocol/capabilities` endpoints.

Do not commit API keys, SMTP credentials, OAuth secrets, access tokens or private signing credentials.

## Reliability checks

GitHub Actions includes regression/build workflows for Android APK compilation, authentication, protocol capabilities, clean server-v2 verification, maintenance isolation, native UI hardening and other subsystems.

The 1|3|7 migration adds explicit regression targets:

- exactly seven canonical Fano specialist home positions and seven Fano lines;
- both hemispheres receive all seven projections;
- Front is canonical and legacy `consensus` is alias-only;
- exactly eleven persisted cores per society;
- Interface does not recursively feed Front;
- peer/local-global feedback re-enters through all seven senses;
- Front/Interface appraisal dimensions are bounded and externalizable only as summaries/control state;
- protected identity, account isolation, zero-API deterministic cycles and selective-no-overwrite sync remain intact.

Before treating a build as released, verify the actual CI result and artifact/download branch rather than inferring success from a version bump or commit alone.

For the staged migration plan, see `JANUS_137_SENSORY_IMPLEMENTATION_PLAN.md`. Historical checkpoints remain valuable evidence of how the architecture evolved; do not rewrite them to pretend the current mapping existed earlier.
