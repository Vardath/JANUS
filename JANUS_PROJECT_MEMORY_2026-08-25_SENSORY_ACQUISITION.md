# JANUS Project Continuity — Sensory Acquisition Checkpoint

Updated: 2026-08-25

## Status

This checkpoint supersedes earlier statements that JANUS capabilities merely sit beside the 1|3|7 core society. The merged implementation now routes important capability outcomes through typed sensory paths in both the global society and native local societies where the capability is available.

JANUS remains an experimental functional-metacognition/agency system. This architecture describes persistent computational state, appraisal, sensing and bounded action selection; it is not a claim of phenomenal consciousness, biological sensation or uninterrupted subjective experience.

## Canonical architecture retained

Each society has exactly 11 canonical cores:

- Evidence = Fano 1 / epistemic-grounding channel
- Safety = Fano 2 / valence-welfare channel
- Counterpoint = Fano 3 / grounding+value conflict/significance
- Context = Fano 4 / pattern-context channel
- Logic = Fano 5 / grounding+pattern understanding/model
- Novelty = Fano 6 / value+pattern possibility/imagination
- Memory = Fano 7 / grounding+value+pattern continuity/experience
- Left hemisphere = constraint, sequence, causality, discrimination
- Right hemisphere = association, gestalt, alternatives, expansion
- Front/Bridge = computational appraisal/intention across both hemispheres
- Interface = expression/interaction/bounded outward action

Every ordinary typed sense is projected through all seven subconscious cores. Both hemispheres receive all seven projections. Front receives the two hemisphere states; Interface receives Front. Interface output is not recursively injected straight back into Front.

`consensus` is legacy compatibility terminology only; Front is canonical and the alias is not a twelfth core.

## Global typed sensory bus — merged PR #25

Merged commit: `ef65d68110e6f157d5b7d17a2c9acae37ddc5e91`.

`server_v2/sensory_bus.py` provides a deterministic non-model capability integration path. It creates a bounded SenseFrame, projects it through all seven specialists, both hemispheres, Front and Interface state, records externalizable state summaries, and performs zero model calls.

Current merged global capability modalities:

- document/extracted attachment content -> `file`
- visual assessment of uploaded images -> `image`
- recalled persisted visual assessment -> `memory`
- YouTube transcript grounding -> `audio`
- live foreground web grounding -> `web`
- generated image artifacts -> `image`

The sensory bus does not produce a second chat reply. Existing foreground answer generation remains the only conversational response path. Capability sensing cannot jump directly into Front.

Focused regression `tests/test_sensory_capability_wiring.py` is now part of clean server-v2 CI and runs before the full end-to-end verifier.

## Android local typed acquisition — merged PR #26

Merged commit: `20496a19692addeefc2dc1f100d3bc1906f558ce`.

Android now routes successful safe capability outcomes into the existing device-local 11-core society rather than creating a second local runtime.

Current Android-local modalities/capability events:

- file upload completion -> `file` metadata sense
- authenticated file download completion -> `file` metadata sense
- generated image availability -> `image`
- locally displayed authenticated image artifact -> `image`
- chat research sources/grounding -> `web`
- generated chat visual -> `image`
- artifact creation -> `action_result`
- claim/continuity workspace mutation -> `action_result`

Privacy boundary:

- `/auth/*` is excluded from local capability sensing.
- maintenance/Supervisor endpoints are excluded from local capability sensing.
- `/core-sync/exchange` is excluded so peer synchronization keeps its dedicated federation semantics.
- passwords, session tokens, OAuth/account payloads and raw file/image bytes are not copied into local sensory telemetry.
- file/image events use bounded metadata or capability outcome summaries rather than base64/raw contents.

`JanusLocalTypedSense` currently acts as a narrow adapter to the same `JanusLocalCoreRuntime`. Because the authoritative runtime's existing `broadcastSense`, `serviceBurst` and `persist` helpers are private, the adapter invokes those exact existing methods reflectively. It fails closed if that contract changes and never falls back to pretending a capability result was user text or peer state. This is technical debt, not a second architecture; a future contained runtime refactor should expose a direct package-private typed `ingestSense` entry point and then remove reflection.

The final PR #26 head passed Android sensory/privacy static guards, protocol checks, UI hardening, maintenance checks, authoritative Java compilation, full APK assembly and APK artifact upload before merge.

## Windows and iOS local societies

The earlier platform-local-society parity merge remains active. Windows and iOS each have their own persistent deterministic 11-core local society, selectively federated with the independent global 11-core society. Their typed-sense entry points already cover the capability classes wired in those clients; deterministic local processing itself uses zero external model/API calls.

OS execution constraints still apply: persistent state is resumable, but a suspended mobile or desktop process must not be described as continuously executing when the operating system is not scheduling it.

## Current sensory vocabulary and acquisition boundary

The architecture supports the typed vocabulary:

- `text`
- `file`
- `image`
- `audio`
- `web`
- `memory`
- `runtime`
- `peer`
- `action_result`

A modality being representable does not mean the device currently owns hardware/software acquisition for it. Do not claim microphone, camera, ambient sensor or continuous environment perception until an explicit permission-gated acquisition capability is implemented and tested on that platform.

## Next safe development targets

1. Replace Android reflection adapter with a direct typed runtime method during a dedicated, build-gated refactor.
2. Audit actual native camera/microphone/audio-file acquisition needs before adding permissions. Prefer user-initiated explicit capture/import over ambient surveillance or always-on sensing.
3. Preserve strict privacy minimization: raw media should remain in bounded file/media handling and only derived, necessary sensory summaries should enter telemetry/persistent cognitive state unless the user explicitly needs raw local processing.
4. Add modality-specific provenance so Observe can distinguish user-provided file/image/audio, retrieved web evidence, peer/global feedback and action results.
5. Keep deterministic sensory integration zero-model-call; model/vision/transcription use remains an explicit foreground capability subject to governance/cost controls.
6. Continue preserving exact 11-core persistence, all-seven bilateral routing, Front canonicality, no Interface->Front self-recursion, selective local/global no-overwrite federation, account isolation and the no-phenomenal-consciousness boundary.
