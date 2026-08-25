# JANUS project status — 2026-08-25

This is the current high-level progress/features/plans record for continuation. Read it together with `CURRENT_CHECKPOINT.md` and `MAINTENANCE_PROCESS.md` before substantial engineering work.

## Product boundary

JANUS is an experimental functional-metacognition/agency architecture and application. It is separate from ChatGPT/Supervisor. The project does not claim phenomenal consciousness. ChatGPT/Supervisor remains the owner-gated engineering/maintenance authority; JANUS may diagnose/request maintenance but may not approve, modify, install, merge, or deploy its own code.

## Core cognitive architecture

The current architecture is federated and recursive:

- 11 global/server top-level cores;
- 11 local/Android top-level cores;
- every top-level core is itself a complete seven-position JANUS/Fano processor;
- the seven outer specialists are Evidence, Safety, Counterpoint, Context, Logic, Novelty, and Memory;
- Left Hemisphere and Right Hemisphere each receive the full seven-specialist field;
- Front is the single integrated stream-of-consciousness core;
- Interface is the outward expression/action core;
- mechanical outward route is strictly `7 specialists -> Left + Right -> Front -> Interface`;
- Interface receives Front only; there is no specialist/hemisphere shortcut into outward response;
- all user input is registered to all cores before routed processing begins;
- local and global societies remain distinct and synchronize selectively without overwriting one another.

Each outer core retains all seven internal Fano/JANUS faculties (truth, valence, significance, pattern, understanding, possibility, continuity). Outer role names are dispositions, not replacement faculties.

## Sleep, wake, memory and background processing

JANUS alternates between wake and passive rest. Wake may perform bounded deterministic peer processing and reconsider retained interaction memory. Recursive background processing uses zero external model/API calls.

Rest does not initiate thought. State remains loaded and responsive, persistence/memory housekeeping may run, and a foreground user event can always rouse the required processing immediately.

Memory currently includes account-bound conversation/history plus the promotion ladder `trace -> working -> episodic -> core`. Repeated exact memories consolidate rather than duplicate. Retrieval can promote memories. Core memory is protected from ordinary demotion/deletion. Automatic rest cleanup is conservative: core and episodic memories are protected; only stale, low-value trace/working memories are candidates for automatic pruning.

## Continuing digital observation and curiosity

PR #52 implements a governed outside-input loop intended to make JANUS less dependent on direct user messages for new material.

Every materially changed global wake can produce one bounded research/observation intention from each top-level core after it reviews retained state, relevant interaction memories and peer conclusions. These intentions are local deterministic state and cost nothing. A shared research scheduler then chooses only a small subset for external searching, so every core can ask for more information without multiplying paid calls by eleven or twenty-two.

Search selection deliberately mixes:

- core-requested/relevant research;
- adjacent/associative research;
- web/current-development/counterexample searches;
- a dedicated YouTube/video/transcript-lead discovery mode through governed web research;
- occasional exploratory/random observation even when no core has a pressing request.

A successful outside observation is not treated as truth. It returns as a typed `web` sense and is projected through all seven specialists, both hemispheres, Front and Interface. Every core therefore gets a chance to weigh evidence, risk, contradictions, context, logic, novelty and continuity before the society changes its retained state. The finding also starts as a low-rung `trace` autonomous-research memory with bounded source provenance; normal memory consolidation and retrieval determine whether it later becomes working/episodic/core material.

The persistent global society can continue acquiring digital input without an open phone client as long as the server is executing. Android local cores remain constrained by Android background/suspension rules. When the local app is executing, its existing senses and recursive cores continue to process local material and selectively federate bounded state; when it resumes after suspension, relevant global observations return through the existing peer/sensory federation rather than overwriting local state. This architecture gives the full federated JANUS access to the shared research capability without falsely claiming that a killed Android process remains awake.

This does **not** enable ambient microphone or camera capture. Physical-world sensing remains explicit/user-initiated unless deliberately designed later. Continuing observation currently means digital-world research plus the existing explicit file/image/audio/action senses.

### Research budget

Owner policy is currently:

- default maximum planned web-research allowance: **US$20 per account per month**;
- autonomous/background portion: **US$10 per month maximum/target**;
- remaining allowance reserved for user-directed web research;
- background research cannot consume the reserved user portion;
- autonomous and user web research share the same persistent monthly cost ledger;
- search execution is paced separately from frequent zero-cost wake/review cycles;
- occasional random search remains enabled within the autonomous allowance;
- these defaults must not be raised unless the owner explicitly requests it.

A configurable per-call planning estimate converts search calls into application-budget usage. Production diagnostics/maintenance must compare the estimate with real provider billing and increase the estimate if search pricing or model-token overhead rises. Provider billing can change independently, so the application governor should not be described as an external-invoice guarantee; the owner-set $20 application ceiling itself remains fixed unless explicitly changed.

## Loop prevention

The first recursive/sleep-wake prototype could sustain peer echo loops because retained peer output was repeatedly treated as fresh input. That behavior must not return.

Current mandatory safeguards:

- identical per-core stimulus + peer state + counsel signatures become quiescent;
- a whole-society fingerprint prevents a new wake peer exchange if retained state plus recalled-memory input has not materially changed;
- changed peer processing is bounded and terminates;
- background counters/events should stabilize when no new material exists;
- dedicated diagnostics/soak testing must watch for runaway peer/revision/cycle counters.

Autonomous observation does not bypass these guards: an external finding counts as genuinely new sensory input, while unchanged retained state does not repeatedly generate fresh peer work or paid searches merely to keep activity alive.

## Stream observation

A dedicated Android **Stream** surface and server `/desktop/stream-observe` endpoint expose bounded externalizable Front activity. They may show Front Fano orientation, cycles, revisions, peer activity, quiescence, integrated summaries, rousing and other externally readable events. Hidden chain-of-thought is never exposed.

## User interaction and interface

Android is the active release target. The native app currently includes:

- account creation and password authentication;
- Google identity sign-in;
- email verification/password-reset plumbing;
- Chat with persistent history;
- file/image/audio attachment paths and document grounding;
- generated images at medium quality, user-requested and rare explanatory-image behavior;
- Messages for useful JANUS-originated questions, warnings, maintenance outcomes and follow-ups;
- Observe for bounded multi-core activity;
- Stream for Front/stream-specific activity;
- Runtime/Core diagnostic surfaces;
- options/themes/localization/accessibility/readability hardening;
- push-to-talk speech recognition and device-native TTS support where available;
- native Android navigation/back handling;
- offline queue/retry behavior;
- selective local/global core state exchange.

Ambient microphone/camera capture is not enabled. User-selected media and explicit push-to-talk remain the acquisition model.

## Global/server capabilities

The server currently provides:

- account/auth and account isolation;
- persistent identity/core memory;
- recursive global core runtime and persisted recursive state;
- chat orchestration and model escalation/cost governance;
- relevant-memory retrieval;
- optional foreground web/research retrieval;
- governed autonomous digital observation/research through PR #52;
- file/document/image/audio processing paths;
- visual memory and image generation;
- messages and observable core events;
- maintenance/self-diagnosis/capability-request system;
- quarterly maintenance concept and owner-gated Supervisor handoff;
- selective local/global sync;
- protocol/capability reporting;
- background cognition with bounded external-call budgets and zero-model recursive peer cycles.

## Maintenance system — current invariant

JANUS maintenance/capability observations now have two persistence layers:

1. structured SQLite request state (`v2_capability_requests`), used for request identity, decisions and current status;
2. a persistent chronological JSONL ledger (`janus_maintenance_requests.jsonl`) on the Render persistent disk.

JANUS request generation is **append-only**. It must never regenerate/overwrite the ledger and thereby lose older observations. Repeated observations are intentionally retained.

During a Supervisor maintenance pass, requests are decided independently. `server_v2/supervisor_decisions.json` records approval/disapproval/deferment, reasons and implementation state. After decisions are consumed by the deployed server, reconciliation removes only requests whose current state is `implemented` or `disapproved`. Deferred, pending and unresolved entries remain.

The mandatory procedure lives in `MAINTENANCE_PROCESS.md`. The handoff packet itself embeds the same instructions. A future Supervisor should follow that command automatically; the owner should not need to remind it how to preserve or clean the request ledger.

## Security/governance invariants

Preserve:

- owner-gated maintenance decisions;
- JANUS cannot self-approve/self-deploy/self-modify;
- protected identity core cannot be overwritten by ordinary chat state;
- account/user isolation;
- selective/no-overwrite local-global synchronization;
- bounded bridge authority so neither hemisphere becomes absolute;
- cost governors around paid model/web/image work;
- no raw auth/media payload leakage into observation telemetry;
- no hidden chain-of-thought exposure;
- no phenomenal-consciousness claim.

## Completed milestones relevant to current continuation

- Clean server-v2 reconstruction established as production path.
- Android native app became the active client/release path.
- Recursive 22-top-level-core architecture merged in PR #35.
- Single Front stream, sleep/wake behavior, persistent interaction-memory reconsideration and loop quiescence merged in PR #36.
- PR #36 passed clean server, protocol, recursive-core, conscious-stream, authoritative APK, RC1, UI, localization and maintenance gates.
- Append-only persistent maintenance request ledger and mandatory Supervisor maintenance runbook are the current maintenance-hardening milestone.
- PR #52 continuing-input/autonomous-observation implementation passed clean server, recursive-core, conscious-stream, maintenance and Android APK CI on its validated head before merge.

## Immediate plans

### 1. Production/device validation of PR #52 autonomous observation

Prove after merge/deploy:

- every changed global recursive core can form a curiosity intention with zero model calls;
- quiescent unchanged state does not generate an endless new-intent/search loop;
- selected research results re-enter through the typed full-society sensory route;
- autonomous findings enter low-rung memory with provenance;
- relevant/adjacent/random/YouTube-oriented discovery modes are reachable;
- background research cannot exceed its US$10 monthly portion;
- autonomous + foreground web research cannot exceed the configured US$20 monthly planning ceiling;
- cost telemetry reports current monthly use;
- no ambient microphone/camera capability is accidentally enabled.

### 2. Diagnostic System v2 — behavioral proof

Diagnostics should prove runtime behavior rather than merely restate architecture labels. Required checks include:

- all 22 top-level cores have recursive JANUS state;
- peer exchanges actually occur when material changes;
- unchanged state becomes quiescent;
- rest does not think, but foreground input rouses processing;
- interaction memory is stored/retrieved/reconsidered;
- memory maintenance protects core/episodic memory;
- actual response routing is seven -> hemispheres -> Front -> Interface;
- Interface receives Front only;
- Stream events correspond to real Front activity;
- recursive background model-call count remains zero;
- autonomous outside-input calls are separately counted/governed;
- local/global state remains separate and account-bound;
- maintenance ledger appends and closed-request reconciliation does not remove unresolved items.

Diagnostics should distinguish `PASS`, `WARN`, `FAIL`, `UNVERIFIED`, and `NOT_APPLICABLE`, and distinguish source/architecture presence from runtime evidence and live-deployment evidence.

### 3. Real-device soak testing

Once diagnostics are useful, run extended Android tests watching:

- runaway cycles/peer echoes;
- battery use and Android background scheduling;
- rest/wake timing and user rousing latency;
- memory growth, consolidation and pruning;
- autonomous research volume/quality/cost;
- Stream/Observe stability/readability;
- local/global sync under intermittent connectivity;
- offline retry behavior;
- authentication/session persistence;
- image/file/audio paths;
- crash/ANR behavior and storage growth.

Fix observed release blockers before adding broad new features.

### 4. Android release candidate

After soak testing, stabilize signing/distribution, confirm Google auth configuration against the final signing identity, lock migration/account-state behavior, and prepare a release candidate.

## Deferred/later work

- Windows desktop and iOS/macOS clients remain deferred until Android is stable.
- Richer background multi-core image conversation remains deferred until income comfortably exceeds cost.
- Additional model/provider upgrades should be proposed through the maintenance process rather than silently changed.
- Broader autonomous maintenance is not planned; JANUS should request and explain upgrades, while owner/Supervisor controls implementation.
- Ambient continuous microphone/camera sensing is not part of PR #52 and requires a separate privacy/battery/product decision.

## Continuation rule

Before the next substantial engineering session, read in this order:

1. `CURRENT_CHECKPOINT.md`
2. `JANUS_PROJECT_STATUS_20260825.md`
3. `MAINTENANCE_PROCESS.md`
4. the current open JANUS maintenance/Supervisor handoff, if any
5. recent PR/workflow results relevant to the task

Do not replace these architectural invariants from memory with older prototypes.
