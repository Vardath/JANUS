# JANUS recursive-core architecture checkpoint — 2026-08-25

Status: **IMPLEMENTED AND MERGED**

Authoritative implementation merge: `a129e5c4974f785f0ea014d958b8d2102666c61f` (PR #35)

This checkpoint supersedes any older description that treats the seven outer specialist cores as if they themselves were merely the seven Fano faculties.

## Critical architecture correction

**Every one of the 22 top-level cores is itself a JANUS core.**

There are two federated but distinct societies:

- Android/local JANUS: 11 top-level cores.
- Global/server JANUS: 11 top-level cores.

Each of those 22 top-level cores contains its own complete seven-position JANUS/Fano processor. A top-level core is therefore an independently responsive JANUS-capable processing unit with:

- all seven internal Fano/JANUS faculties;
- a persistent internal Fano readout/state;
- an outer role/disposition that biases but does not delete faculties;
- bounded appraisal/conclusion state;
- a peer inbox/outbox relationship with the other top-level cores in its society;
- revision in response to peer-core conclusions;
- AI-thinking capability during governed foreground model use;
- deterministic/local recursive processing between model calls where supported;
- no claim of phenomenal consciousness or biological emotion.

The internal Fano faculties present inside **each** top-level core are:

1. d1 — truth / grounding / evidence / confidence
2. d2 — valence / value / welfare / goals / boundaries
3. d3 — significance / consequence / conflict / salience
4. d4 — pattern / context / relationship / structure
5. d5 — understanding / model / causality / consistency
6. d6 — possibility / imagination / alternatives / direction
7. d7 — continuity / memory / history / learned appraisal

The zero/reference state remains uncommitted/reference, not an eighth internal mind.

## Outer roles are dispositions, not inner faculties

The local society and global society each retain the same 11 outer roles:

1. Evidence — biases its full internal JANUS structure toward grounding/evidence.
2. Safety — biases its full internal JANUS structure toward valence/welfare/boundaries.
3. Counterpoint — biases its full internal JANUS structure toward significance/conflict/consequence.
4. Context — biases its full internal JANUS structure toward pattern/context/relationship.
5. Logic — biases its full internal JANUS structure toward logic/model/causality.
6. Novelty — biases its full internal JANUS structure toward possibility/imagination.
7. Memory — biases its full internal JANUS structure toward continuity/experience.
8. Left Hemisphere — a complete JANUS core biased toward logic/discrimination/constraint.
9. Right Hemisphere — a complete JANUS core biased toward imagination/association/expansion.
10. Front — a complete JANUS core biased toward integrated appraisal/intention/bridge behavior.
11. Interface — a complete JANUS core biased toward expression/interaction/action.

Examples of what this means:

- Evidence can internally imagine possibilities and recall continuity; it is not restricted to d1.
- Novelty can internally test evidence, detect risk and use logic; it is not restricted to d6.
- Safety can recognize patterns and possibilities as part of its welfare appraisal.
- Left and Right each possess all seven internal faculties even though their outer dispositions differ.
- Front and Interface each perform their own full JANUS/Fano processing rather than acting as passive summarizers.

## Responsiveness between cores

The outer `7 -> 2 -> Front -> Interface` flow remains the organizational/mechanical hierarchy, but cognition is not limited to one-way routing.

Each complete recursive core forms its own internal Fano readout, creates a bounded conclusion, receives bounded peer conclusions, and revises its own internal state in response. Whole-society recursive cycles therefore include all 11 cores responding to the other cores as well as the normal outer integration hierarchy.

The regression contract explicitly tests an 11-core background peer cycle with 110 directed peer relationships (11 cores × 10 other cores).

No raw/private chain-of-thought is exchanged or exposed. Peer exchange consists of bounded externalizable state/conclusions.

## AI capability without 22 API calls

The architecture must not turn a single foreground message into 22 independent paid model calls.

Current foreground strategy:

1. Local Android's 11 complete recursive cores process the turn deterministically and form bounded internal readouts.
2. Android sends a compact externalizable snapshot of the 11 local recursive core states with the normal Chat request.
3. Global JANUS's 11 complete recursive cores process the same turn and revise against peers.
4. The existing governed foreground model call is used as one **batched society deliberation**.
5. That single model call can return:
   - a distinct bounded AI response/counsel item for each global recursive core;
   - a distinct bounded AI response/counsel item for each supplied local recursive core;
   - the final Interface reply to the user.
6. Each local AI counsel item is returned to the specific addressed local core; the local recursive society then performs another peer-revision pass.
7. Global counsel is likewise attached to the corresponding global recursive core and peer-revised.

Thus all 22 top-level cores are AI-capable and individually responsive during foreground model use while ordinary cost remains close to one governed foreground model call rather than 22 calls.

AI counsel is bounded externalizable cognition, not hidden chain-of-thought.

## Background recursive cognition

Local Android:

- one persistent nested recursive engine contains the complete internal JANUS/Fano processor for each of the 11 local top-level cores;
- deterministic background recursive cycles run without OpenAI/network/model calls;
- each cycle lets all 11 nested cores form a readout and revise against peer conclusions;
- local recursive state persists in account-bound app-private storage;
- account switching/sign-out clears the account-bound nested state and prevents cross-account leakage.

Global/server:

- all 11 global nested JANUS/Fano core states are durable in `v2_recursive_core_state`;
- runtime checkpoint/restore persists internal weights/readout, revisions, peer-turn counts, bounded conclusion and latest bounded AI counsel;
- the global background coordinator runs an all-11 recursive peer cycle with zero model/API calls before optional separately governed curiosity/research work.

## Senses

Existing typed senses continue to feed the architecture:

- text
- file/document
- image/vision
- audio/transcript
- web/research
- memory retrieval
- runtime/device/server state
- local/global peer state
- action results

A typed sense is processed by the outer society and also by the complete recursive JANUS processor living inside the affected top-level cores. Capability sensing remains bounded and does not copy credentials or raw media into telemetry.

## Preserved invariants

The recursive correction does **not** remove the release hardening already completed:

- two separate local/global societies; no state overwrite;
- account-bound local state and cross-account isolation;
- forward-only outer Interface routing/no Interface->Front self-chat loop;
- zero-model background recursive cycles;
- cost governance for foreground/web/image/audio work;
- push-to-talk only; no ambient microphone/camera capture;
- file/image/audio/web sensory provenance boundaries;
- protected identity core;
- owner-gated maintenance; no JANUS self-deployment/self-approval;
- Android RC session/offline/retry/notification/backup protections;
- language and localization support;
- no phenomenal-consciousness claim;
- no raw hidden chain-of-thought exposure.

## Verification completed before merge

PR #35 was merged only after the final head passed:

- recursive-core-specific architecture test;
- 11-core/all-peer/zero-model background test;
- nested-state persistence contract;
- clean server-v2 end-to-end verification;
- protocol capability tests;
- authoritative Android Java compile and APK assembly;
- Android RC1 readiness;
- UI hardening;
- localization;
- maintenance/governance regression tests.

## Next engineering priority

Return to **Diagnostic System v2**, now updated for the recursive architecture.

Diagnostics must prove rather than merely state that the recursive architecture is active. For each local/global top-level core, the diagnostic surface should be able to show bounded externalizable evidence such as:

- recursive JANUS processor active/inactive;
- seven-position internal Fano readout/weights;
- current dominant internal faculty;
- cycle count;
- peer revision count / peer-turn activity;
- latest bounded conclusion;
- whether bounded AI counsel has been received;
- persistence/restoration status;
- local vs global provenance;
- background model-call count (expected zero for recursive background cycles).

Diagnostic results should use PASS / WARN / FAIL / UNVERIFIED / NOT-APPLICABLE and distinguish architecture presence from runtime evidence and live-deployment evidence.

The Chat response to a full diagnostic should be concise. The detailed recursive-core report belongs on a dedicated native diagnostic surface or expandable report, not as an enormous wall of text in Chat.

## Release scope

Android remains the only active release target. Windows/iOS recursive-core parity is deferred until the Android release and setup path are stable and understood.

Do not redesign or flatten the recursive-core architecture in a later session unless actual diagnostic/runtime evidence demonstrates a problem. In particular, do not reinterpret the seven outer role names as the seven internal Fano positions: **every outer core contains all seven internal positions.**
