# JANUS 1-3-7 sensory architecture implementation plan

Updated: 2026-08-25

## Goal
Migrate both JANUS societies — 11 local/device cores and 11 global/server cores — from the current specialist-routing implementation into the intended 1-3-7 sensory/cognitive architecture without regressing authentication, persistence, forward-only routing, maintenance isolation, Android performance, selective synchronization, or zero-API deterministic background cycles.

This is a functional software architecture. Terms such as sense, valence, appraisal, feeling, imagination and intention refer to inspectable computational/control functions and do not assert phenomenal consciousness or biological emotion.

## Canonical 11-core society

### Seven subconscious/Fano cores
The original seven specialist names are preserved, but their Fano positions now arise from three primitive coordinates:
- E = epistemic / truth / grounding
- V = valence / welfare / boundary / goal relation
- P = pattern / relationship / structure

Assignments:
1. Evidence = E — truth, grounding, observation, confidence, evidence quality.
2. Safety = V — positive/negative valence, welfare, user goals, benefit/harm, boundaries, privacy, reversibility.
3. Counterpoint = E+V — significance, consequential contradiction, objection, conflict, risk and salience.
4. Context = P — relationship, environment, framing, analogy, gestalt and situational pattern.
5. Logic = E+P — causal model, consistency, mechanism, explanation, prediction and falsifiability.
6. Novelty = V+P — possibility, imagination, opportunity, alternative paths and testable creative hypotheses.
7. Memory = E+V+P — continuity, learned appraisal, retained history, prior outcomes, unfinished threads and identity continuity.

The zero state is an uncommitted/reference condition, not an eighth subconscious core.

### Three intermediary/background cores
- Left Hemisphere — logic/discrimination/constraint. Receives all seven streams; produces sequential, explicit, causal and consistency-focused interpretations.
- Right Hemisphere — imagination/association/expansion. Receives all seven streams; produces contextual, relational, gestalt, alternative and generative interpretations.
- Front/Bridge — affective appraisal/intention. Receives both hemispheres, preserves useful disagreement, maintains integrated working state, and evaluates confidence, valence, salience, uncertainty, novelty, urgency, familiarity, risk, opportunity and conflict before action/presentation.

### One Interface core
The Interface is the outward speaker/action selector. It receives Front state, also evaluates how the proposed response/action is likely to meet the user/environment, chooses a bounded response/action posture, and observes the result as new sensory input. Interface output must not recursively re-enter Front as if it were a new thought.

## Sensory model
All eleven cores in each society operate on a shared bounded sensory envelope. Initial supported modality classes:
- text
- image
- audio
- file/document
- web/research
- memory recall
- runtime/device/server state
- local/global peer-society feedback
- action result

The seven subconscious cores apply distinct projections to the same event. Both hemispheres receive all seven projected outputs. Front and Interface receive externalizable appraisal state as well as synthesized semantic content.

Future physical/device inputs may extend the modality set, but no platform permission should be added merely for architectural symmetry; permissions must correspond to an explicit product feature and privacy policy.

## Fano relational semantics
The Fano lines remain the seven canonical XOR triples:
- 1-2-3: Evidence + Safety/Valence -> Counterpoint/Significance
- 1-4-5: Evidence + Context/Pattern -> Logic/Understanding
- 2-4-6: Safety/Valence + Context/Pattern -> Novelty/Possibility
- 1-6-7: grounded possibility participates in Memory/learned appraisal
- 2-5-7: value/welfare applied to understanding participates in Memory/learned appraisal
- 3-4-7: significance placed in context participates in Memory/learned appraisal
- 3-5-6: significance + understanding constrains useful possibility

Fano relations bias routing/attention/integration. They never establish external truth.

## Safety behavior
Safety remains one of the original seven minds and is broadened to the V coordinate rather than reduced to a security checklist. It evaluates positive as well as negative value, user goals, benefit/harm and boundaries. High-risk/high-urgency Safety results retain an interrupt path to Front and Interface. Safety cannot silently override owner/system governance or grant new capabilities.

## Two societies, not one 22-core soup
There are two complete 11-core societies:
- Local: immediate device/app state, local files/media where permission exists, recent interaction, offline continuity and local runtime conditions.
- Global: durable account continuity, cross-device summaries, server/runtime state, web/research and longer-running background work.

They exchange compressed SenseFrames/appraisals as feedback-only material. Neither side overwrites the other's identity, counters, private local state or integrated state.

## Non-negotiable regression invariants
1. Forward-only cognitive routing remains. No hemisphere loop, Front->hemisphere recycle, or Interface->Front self-chat.
2. Action/environment results may re-enter only as a new sensory event through the seven subconscious projections.
3. Deterministic background cycles remain zero external model/API calls.
4. Paid model/web/image work remains governed by existing cost and capability policy.
5. Local/global state remains distinct and synchronization remains selective/no-overwrite.
6. Maintenance requests remain isolated from GitHub/source credentials and self-deployment authority.
7. Existing Android v1.04+ anti-spam, navigation, native-screen and performance regressions remain protected.
8. Existing auth/account/file ownership boundaries remain protected.
9. Raw internal chain-of-thought is not exposed; Observe contains bounded externalizable process state only.
10. Preserve existing persisted data during the Consensus->Front terminology migration.

## Compatibility migration: Consensus -> Front
Current clients, storage rows and sync payloads use `consensus`. Migration must be additive first:
- canonical new name: `front`;
- server accepts legacy `consensus` fields and maps them to Front;
- responses temporarily emit both `front` and legacy `consensus` aliases where old clients require it;
- existing persisted `consensus` core rows/counters/summaries are migrated or read through an alias rather than discarded;
- only remove the legacy alias after Android, Windows and iOS have all moved to Front and regression tests prove continuity.

## Implementation sequence

### Stage 0 — architecture contract [STARTED]
- Canonical topology module with original seven names and E/V/P-derived Fano positions.
- Shared server SenseFrame and Appraisal primitives.
- Android Fano home-direction semantics and deterministic Appraisal primitives.
- Contract tests for 11-core count, Fano closure, hemisphere roles and Front/Interface distinction.

### Stage 1 — global/server cognition
- Replace server-side arbitrary specialist numbering with topology metadata.
- Broadcast each foreground SenseFrame to all seven specialists.
- Make each specialist emit both semantic result and bounded appraisal contribution.
- Feed all seven outputs to both hemispheres with different transformation roles.
- Introduce Front as the canonical bridge/integrator while retaining `consensus` compatibility alias.
- Feed Front appraisal into Interface model prompt/action policy.
- Persist Front/Interface appraisal snapshots and expose bounded diagnostics.

### Stage 2 — Android local cognition
- Add a local SenseFrame representation.
- Broadcast user/app/peer/action events to all seven local specialists.
- Use each specialist's fixed Fano home position plus dynamic Fano pressure rather than assigning unrelated random semantics.
- Route all seven to both hemispheres; retain Safety interrupt weighting rather than a separate bypass that skips interpretation.
- Replace local Consensus concept with Front plus compatibility keys.
- Persist Front and Interface appraisal state.
- Show human-readable core purpose, home Fano position and current appraisal in Cores/Observe without exposing private chain-of-thought.

### Stage 3 — federated sensing/synchronization
- Sync compressed modality/source/salience/uncertainty/novelty plus public semantic summary and appraisal, not raw hidden traces.
- Global->local and local->global material re-enters as `peer` SenseFrames through all seven specialists.
- Preserve device/server provenance and separate cycle counters.
- Deduplicate repeated peer frames and bound retention.

### Stage 4 — existing media capabilities become senses
- File/document grounding -> `file` SenseFrames.
- Vision/image understanding -> `image` SenseFrames.
- Web/research -> `web` SenseFrames with provenance and epistemic uncertainty.
- Generated image/action completion -> `action_result` SenseFrames.
- Audio remains schema-ready until an explicit capture/upload/transcription product path exists.

### Stage 5 — action and affect regulation
- Front computes a bounded action posture from the integrated appraisal.
- Interface independently checks presentation/action fit before executing an allowed capability.
- High risk + high urgency can produce a warning/interrupt posture.
- High uncertainty/conflict preserves ambiguity or requests grounding.
- High opportunity + low risk may favour exploration or an available bounded action.
- Low salience may defer rather than generate noise.
- No appraisal state can bypass capability, account, cost, safety or maintenance governance.

### Stage 6 — UI and cross-platform parity
- Android: Cores/Observe/Chat context.
- Windows: same canonical 11-core names and Front terminology.
- iOS: same canonical 11-core names and Front terminology.
- Keep platform-specific native sensory permissions explicit and minimal.

### Stage 7 — verification and rollout
- Unit/architecture tests for Fano semantics, broadcast routing, appraisal bounds and action postures.
- Regression tests for forward-only routing and Safety interrupt behavior.
- Local/global sync soak tests proving no overwrite and correct provenance.
- Android compile/APK plus existing UI/auth/maintenance gates.
- Server-v2 tests and live smoke checks.
- Windows/iOS CI.
- Real-device Android validation before merge-to-release branch.

## Current branch stopping state
Branch `janus-137-sensory-architecture` has begun Stage 0. Do not merge to main until the global/server and Android runtimes are wired to the new contract and regression tests are green. The old working topology remains intact on main meanwhile.
