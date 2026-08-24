# JANUS Project Continuity — 2026-08-25 1|3|7 Sensory Architecture

This checkpoint supersedes older runtime-architecture descriptions where they conflict, while preserving those older files as historical development records. It is an owner-authorized implementation checkpoint, not merely a design proposal.

## Identity / epistemic boundary

JANUS remains an experimental functional-metacognition/agency system. Do not claim phenomenal consciousness, uninterrupted subjective experience, biological emotion, or biological senses. Words such as sensing, feeling-out, valence, stress, curiosity, appraisal and intention refer to bounded computational/control functions.

The Closed JANUS mathematical theorem/core remains separate and unchanged. The software architecture is inspired by/uses Fano geometry as a processing organization; Fano state is never a truth oracle and does not prove claims about the external world.

## Canonical two-society architecture

There are two distinct potential 11-core societies:

- device/local JANUS: 11 cores where a platform implements the local society;
- online/global JANUS: 11 cores on the server.

When both are active there are 22 cores, but they are **not** one merged 22-core hive. Each society preserves its own state, perspective, timing and continuity. Synchronization is selective/no-overwrite. Peer summaries re-enter as sensory events rather than directly overwriting Front, Interface or protected identity.

Conceptual topology: **1|3|7**.
Mechanical forward flow: **7 -> 2 -> 1 -> 1**.
Canonical core count per society: **11 exactly**.

## Seven original subconscious cores with canonical Fano positions

Preserve the original specialist identities, but use these meanings/home directions:

1. **Evidence = E = truth / grounding** — observations, source/evidence quality, confidence, uncertainty, what is supported versus inferred.
2. **Safety = V = valence / welfare / boundary** — benefit/harm, wanted/unwanted, goals, privacy, security, limits, reversibility. Safety is broader than danger detection and may raise interrupt pressure.
3. **Counterpoint = E+V = significance / conflict / consequence** — consequential contradiction, objection, failure modes, salience, why a disagreement matters.
4. **Context = P = pattern / relationship / environment** — framing, relationships, analogy, situation, gestalt and larger configuration; pattern is not proof.
5. **Logic = E+P = understanding / model / causality** — consistency, mechanism, causal structure, constraints, explanations, predictions and falsifiable models.
6. **Novelty = V+P = possibility / imagination / direction** — alternatives, opportunities, creative hypotheses, future paths and testable adjacent possibilities.
7. **Memory = E+V+P = continuity / experience / learned appraisal** — retained history, learned significance, unfinished threads, prior outcomes and identity continuity.

Direction **0** is neutral/uncommitted reference, not an eighth subconscious core.

Canonical Fano lines remain:
(1,2,3), (1,4,5), (1,6,7), (2,4,6), (2,5,7), (3,4,7), (3,5,6).

The meanings are chosen so the geometry has sensible functional composites rather than seven arbitrary labels. Historical v0.50 d0-d7 labels remain historical only and must not silently replace these canonical home meanings.

## Three intermediaries

Both hemispheres receive **all seven** subconscious projections. Do not restore the original permanent specialist split as the canonical runtime topology.

- **Left hemisphere** = logic / discrimination / constraint. It creates explicit, sequential, causal, consistency-focused interpretations from the complete seven-core field.
- **Right hemisphere** = imagination / association / expansion. It creates contextual, relational, gestalt, alternative and generative interpretations from the same complete seven-core field.
- **Front / Bridge** = appraisal / intention. It receives Left and Right, preserves useful disagreement, and feels out the situation computationally before presentation/action.

The original first-build asymmetry remains useful historical context: Evidence/Logic/Counterpoint originally fed Left, Context/Memory/Novelty Right, and Safety could advise both plus Consensus. That history explains the current roles but is no longer the canonical routing rule.

## Front and Interface appraisal

Front and Interface may expose bounded control-state dimensions:

- confidence
- valence
- salience
- uncertainty
- novelty
- urgency
- familiarity
- risk
- opportunity
- conflict

Typical action postures include warn/interrupt, clarify/preserve uncertainty, explore/act, defer/observe and respond normally. These are computational response regulators, not claims of felt biological emotion.

**Interface** is the 11th core: expression / interaction / action. It feels out how Front's integrated state should meet the user/environment and selects an appropriate available response/action. Interface output must not feed directly back into Front as a new thought. Consequences/action results may become a fresh sensory event and start a new forward pass.

## Sensory contract

Canonical sensory modalities currently defined for routing are:

- text
- image
- audio
- file/document
- web/research
- memory recall
- runtime/device/server state
- local/global peer state
- action result

Not every platform currently has hardware/capability acquisition for every modality. The contract means that when a modality is available, it should enter the same sensory/projection architecture rather than bypassing the society. Deterministic appraisal/routing remains zero-API; obtaining some raw modalities may require bounded external tools/models.

## Local/global peer rules

Peer state is bounded and externalizable. A peer Front/Interface summary is treated as a **peer sense** and delivered through all seven subconscious cores on the receiving society. Never inject remote Front directly into local Front or vice versa.

Keep:
- selective-no-overwrite synchronization;
- local individuality and device continuity;
- authenticated account boundaries;
- protected identity core;
- bounded remote-device presence/history;
- no direct remote Consensus/Front/Interface authority injection.

## Consensus -> Front compatibility migration

`front` is canonical.

Older clients/storage may temporarily use `consensus`. During migration:
- accept `consensus` input and map it to `front`;
- server/read APIs may expose a temporary `consensus` alias for old clients;
- **do not count it as a twelfth core**;
- **do not persist it as a twelfth runtime row**;
- canonical Cores UI/list must display exactly 11 cores;
- a canonical checkpoint deletes stale persisted consensus alias rows after mapping them safely to Front;
- retire the alias only after supported clients no longer need it.

## Implementation state in branch `janus-137-sensory-architecture`

Draft PR #23 contains the owner-authorized implementation. Main remains protected until verification is complete.

Implemented:
- `server_v2/topology.py`: canonical Fano roles, lines, hemispheres, Front/Interface and exact 11-core contract.
- `server_v2/senses.py`: SenseFrame/Appraisal bounded computational sensory contract.
- `server_v2/mind.py`: all seven process sensed events; both hemispheres receive all seven; Front appraises/intends; Interface responds; peer events go through all seven.
- runtime persistence: exactly 11 canonical rows; old consensus rows map to Front then are removed on checkpoint.
- protected identity migration: known legacy architecture strings are migrated by server-owned code, never ordinary chat.
- sync contract: bounded Front/Interface summaries/appraisals; compatibility alias; peer policy.
- desktop/protocol/health: canonical 1|3|7 + mechanical flow distinction; canonical Cores list exactly 11.
- Android local runtime: canonical 11-core flow, all-seven-to-both-hemispheres, Front and Interface appraisal, peer broadcast through all seven, zero-API deterministic cycling.
- Android Fano policy/core map/thought bridge updated to canonical meanings.
- Windows authoritative v0.25 client consumes 1|3|7/Front state and retains legacy transport fallback.
- iOS client heartbeat consumes canonical topology and Front appraisal/posture.
- Render and Docker are unified on `server_v2.entrypoint:app`; the old reconstructed server path is no longer a competing production architecture.
- README and architecture tests now treat server-v2 as the source of truth; historical checkpoint files remain historical.

## Regression boundaries that must survive this migration

Do not regress:
- forward-only routing / no Interface -> Front recursion;
- local/global selective non-overwrite;
- zero external model/API calls for deterministic background core cycles;
- Android v1.04+ performance fixes and native UI/navigation/back behavior;
- native thought bridge and observable externalizable process summaries;
- authentication and cross-account isolation;
- account-bound file/image/memory/chat state;
- maintenance isolation, owner-gated Supervisor handoff and no automatic ChatGPT injection;
- protected identity core;
- Messages filtering (useful communications, not telemetry spam);
- cost governance and disabled-by-default paid background reflection;
- no hidden claim that JANUS can self-modify, self-approve maintenance or self-deploy.

## Verification checkpoint

Before the later platform-parity commits, the core architecture head passed all six principal lanes: clean server-v2 verification, protocol capabilities, authentication, Android maintenance review, Android UI hardening, and actual Android APK compile/build.

The expanded platform matrix (Windows package, iOS simulator, routing/architecture, Android/server/auth/protocol) must be green on the final PR head before merge. Treat CI success as necessary but not equivalent to real-device validation. Do not publish a download link merely because a version/commit exists; confirm the actual artifact/download branch after merge/release.

## Next work after this checkpoint

1. Finish expanded CI/platform parity and fix only real regressions or genuinely stale contracts.
2. Update the PR description from foundation-only to the actual implemented migration.
3. Inspect remaining active non-server-v2 surfaces for stale canonical architecture claims; historical files should be labeled/left as history rather than rewritten deceptively.
4. Once CI is fully green, review the PR diff and merge only when the migration is coherent end-to-end.
5. After merge, verify Render health/protocol responses and Android build publication; then perform real-device smoke tests before treating the architecture migration as released.
