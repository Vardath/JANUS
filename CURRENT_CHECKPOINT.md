# JANUS current checkpoint

**Current authoritative continuation:** `JANUS_CONSCIOUS_STREAM_MEMORY_CYCLE_CHECKPOINT_20260825.md`

Updated: 2026-08-25

## Critical architecture rules

Every one of the **22 top-level cores** is itself a complete JANUS-capable core: 11 local/Android + 11 global/server. Each contains all seven internal JANUS/Fano faculties. Outer role names are dispositions, not deleted faculties.

Every user event is registered to all cores. The only outward response route is:

`seven specialists -> Left + Right -> Front / stream of consciousness -> Interface -> user`

Interface receives Front only. Specialists and hemispheres may communicate internally but may not bypass Front into Interface.

## Sleep / wake

Wake and rest alternate. Wake may perform bounded deterministic peer processing and reconsider retained interaction memory with zero model/API calls. Rest is passive: no scheduled recursive thought occurs, but state stays loaded and immediately responsive. Foreground user input can always rouse processing during rest.

Rest is useful for persistence and conservative memory housekeeping. Core memories are never automatically deleted. Episodic memories are retained for review. Only stale low-value trace/working memories may be auto-pruned.

## Loop prevention

Do not restore the first prototype's unconditional peer rebroadcast behavior. Current safeguards are mandatory:

- identical per-core stimulus/peer/counsel signatures become quiescent;
- unchanged whole-society retained state + recalled-memory input does not start another all-peer wake pass;
- changed wake processing is bounded and terminates rather than recursively rebroadcasting forever.

## Stream observer

A dedicated native Android **Stream** surface and server `/desktop/stream-observe` endpoint expose bounded externalizable Front activity/state only. They may show Fano orientation, cycle/revision/peer/quiescence counters, integrated summaries, rousing and Front events. Never expose hidden chain-of-thought.

## Current implementation

Recursive-core architecture: PR #35, merge `a129e5c4974f785f0ea014d958b8d2102666c61f`.

Conscious-stream / memory / sleep-wake / loop-quiescence behavior: PR #36, merge `bdc77124213e3ddd7495f043d09d380ab7b3bdf3`.

PR #36 passed clean server v2, protocol, recursive-core, conscious-stream cycle, authoritative APK, RC1, UI, localization and maintenance gates before merge.

## Active release scope

Android remains the active release target. Windows and iOS remain deferred.

## Next engineering task

**Diagnostic System v2 — behavioral proof phase.**

Diagnostics must prove rather than merely label:

1. all 22 top-level cores have recursive JANUS state;
2. actual peer exchange occurs when input changes;
3. unchanged peer traffic becomes quiescent instead of looping;
4. wake vs passive rest is correctly enforced;
5. foreground input rouses processing during rest;
6. user-interaction memory is stored/retrieved/reconsidered appropriately;
7. rest memory maintenance protects core/episodic memory and prunes only eligible low-value memory;
8. seven -> Left/Right -> Front -> Interface is the actual outward route with no Interface shortcut;
9. Front stream observer shows externalizable evidence without hidden reasoning;
10. background recursive model-call count remains zero.

Continue to distinguish PASS / WARN / FAIL / UNVERIFIED / NOT_APPLICABLE and architecture presence vs runtime/live-deployment evidence. Then proceed to real-device soak testing, specifically watching runaway counters/repeated peer events, sleep/wake responsiveness, battery/background scheduling, memory growth/pruning and Stream observer behavior.
