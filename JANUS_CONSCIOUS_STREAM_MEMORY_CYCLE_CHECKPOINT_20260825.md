# JANUS conscious-stream / memory / sleep-wake checkpoint — 2026-08-25

Authoritative continuation after PR #36 (`bdc77124213e3ddd7495f043d09d380ab7b3bdf3`).

## Non-negotiable cognitive architecture

JANUS remains a federated pair of 11-top-level-core societies (11 local Android + 11 global/server = 22 top-level cores). Every top-level core is itself a complete seven-position JANUS/Fano processor. The seven outer specialist roles are dispositions, not the seven internal faculties.

Every user event is registered to every top-level core. Registration means the core has received the event; it does not itself imply a hidden thought trace.

The only user-facing/outward cognitive route is:

`seven specialists -> Left hemisphere + Right hemisphere -> Front / stream of consciousness -> Interface -> user`

The seven specialist results must reach both hemispheres. Front integrates Left and Right. Interface receives Front only for outward response generation. Specialists and hemispheres may exchange bounded peer state internally, but no specialist or hemisphere may bypass Front into Interface. Interface is an expression/interaction boundary, not an independent competing stream of consciousness.

## Stream of consciousness observer

Front is the single integrated stream-of-consciousness core in the functional architecture. Android now has a native `Stream` observe surface and the server exposes `/desktop/stream-observe`. These surfaces are read-only and show externalizable Front activity/state: current recursive Fano orientation, cycles/revisions/peer turns/quiescence, integrated summaries, rousing events and retained Front events. They must never expose private chain-of-thought.

## Sleep / wake behavior

Wake and rest alternate. During wake, deterministic recursive background cycles may reconsider retained state, recall bounded recent user-interaction memories and exchange bounded peer conclusions. Ordinary recursive wake cycles make zero model/API calls.

Rest is genuinely passive: scheduled recursive `think()` cycles do not run. Recursive state remains loaded and responsive. Rest performs useful non-cognitive housekeeping such as persistence and conservative memory maintenance. Foreground user input always has authority to rouse processing immediately; a user must never be blocked waiting for the next wake window.

## Interaction memory and storage

Foreground conversations are stored account-locally in the existing persistent memory ladder. Relevant memories are retrieved during foreground processing. Changed wake cycles may also recall a bounded recent memory digest so the minds can reconsider prior user interactions between conversations without paying for an external model call.

Rest-phase memory maintenance is conservative:
- core memories are never automatically deleted;
- episodic memories are not automatically deleted and may only be flagged for later review;
- only stale, low-salience, low-access trace/working memories are eligible for automatic pruning;
- memory maintenance emits externalizable maintenance telemetry when it changes anything.

This is storage management, not active thought during sleep.

## Loop prevention — lesson from first implementation

The first sleep/wake prototype (`851bdb6ea0ed26661ac1b7ceae097ebd2a74ecca`) could repeatedly turn peer output into new peer input on every wake tick. With no novelty/deduplication/quiescence boundary, A could cause B, B could cause A, and the society could sustain an echo loop even without an LLM.

The current architecture therefore has two loop barriers:
1. per-core processing signatures: identical stimulus + identical peer state + identical counsel becomes quiescent and does not count as another cognitive revision;
2. whole-society wake fingerprint: if retained outer state plus recalled memory input has not materially changed since the prior wake pass, no new all-peer exchange is started.

When society input changes, a bounded peer pass is allowed. The all-11 global wake pass can process 110 directed peer relationships, but it terminates after the bounded pass. Android uses the same quiescence principle.

## Per-core communication evidence

Actual changed server wake cycles emit a Front `recursive_peer_exchange` event that records the number of recursive cores participating, bounded peer-revision links processed, whether retained interaction memory was available and `model calls=0`. Per-core recursive state retains peer-turn and revision counters. This gives diagnostics evidence that cores are communicating rather than merely assuming it from topology.

## Foreground AI cost strategy

The existing one-call recursive deliberation strategy remains: a governed foreground model call can return bounded distinct counsel for recursive cores, while the user-facing answer is expressed from Front stream state. Interface is not allowed a society-wide shortcut around Front. Background recursive cycles remain zero-model-call.

## Protocol guarantees added

Protocol generation remains server v2 clean reconstruction; cognitive engine generation is `recursive-conscious-stream-v2`. Advertised guarantees include:
- `single_front_outward_stream`
- `interface_front_only_input`
- `interruptible_passive_rest`
- `foreground_rouses_resting_cores`
- `wake_memory_reconsideration`
- `conservative_memory_housekeeping`
- `peer_loop_quiescence`
- `stream_of_consciousness_observe`

## Verification at merge

PR #36 passed all final-head gates before merge:
- clean server v2 end-to-end;
- protocol capabilities;
- recursive core engine;
- new conscious-stream/sleep-memory/loop regression gate;
- authoritative Android APK build;
- Android RC1 readiness;
- UI hardening;
- localization;
- maintenance/self-diagnosis/isolation.

## Next continuation

Continue with Diagnostic System v2, but make it prove the new behavioral contracts at runtime: wake vs passive rest, foreground rousing, Front-only Interface routing, memory recall/maintenance, quiescence/loop suppression and actual bounded peer exchange. Keep the stream observer externalizable-only. Real-device soak testing should specifically watch for runaway revision counters, repeated identical peer events, battery/background scheduling behavior, stale memory growth and user input arriving during rest.
