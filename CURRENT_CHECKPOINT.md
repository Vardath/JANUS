# JANUS current checkpoint

**Current authoritative continuation:** `JANUS_CONSCIOUS_STREAM_MEMORY_CYCLE_CHECKPOINT_20260825.md`

**Current project status:** `JANUS_PROJECT_STATUS_20260825.md`

**Mandatory maintenance runbook:** `MAINTENANCE_PROCESS.md`

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

## Maintenance request persistence

JANUS-generated maintenance/capability observations must be preserved rather than regenerated over one another.

- Structured request state remains in SQLite `v2_capability_requests`.
- A chronological JSONL request ledger is stored on persistent server storage alongside the database (`janus_maintenance_requests.jsonl`).
- JANUS generation is append-only; each generated/repeated observation is appended and never overwrites older entries.
- A Supervisor maintenance pass records decisions in `server_v2/supervisor_decisions.json`.
- After those decisions are consumed, reconciliation removes only entries whose request state is `implemented` or `disapproved`.
- Deferred, pending, repeated and unresolved entries remain.
- The exact procedure is mandatory in `MAINTENANCE_PROCESS.md` and is injected into every Supervisor handoff packet so the owner does not need to restate it.
- Built-in procedure command: `python -m server_v2.maintenance_request_file instructions`.
- Built-in cleanup command for a mounted maintenance environment: `python -m server_v2.maintenance_request_file reconcile`.

Do not replace the ledger with a newly generated snapshot. Do not delete unresolved requests because they are old or duplicated.

## Current implementation

Recursive-core architecture: PR #35, merge `a129e5c4974f785f0ea014d958b8d2102666c61f`.

Conscious-stream / memory / sleep-wake / loop-quiescence behavior: PR #36, merge `bdc77124213e3ddd7495f043d09d380ab7b3bdf3`.

PR #36 passed clean server v2, protocol, recursive-core, conscious-stream cycle, authoritative APK, RC1, UI, localization and maintenance gates before merge.

Current maintenance hardening adds the append-only persistent request ledger, automatic closed-request reconciliation after Supervisor decisions, mandatory `MAINTENANCE_PROCESS.md`, and the comprehensive `JANUS_PROJECT_STATUS_20260825.md` continuation record.

### Android UI stability checkpoint — 2026-08-25

The real-device crash affecting several detail screens persisted after the earlier navigation/surface reset changes. Investigation identified a plausible shared risk: multiple independent Android `OnGlobalLayoutListener`/UI-polish layers were walking and sometimes modifying the same live view hierarchy while detail screens were being laid out.

A stability-first v1.09 build was therefore produced that disables the competing cosmetic/runtime view-tree injection layers while preserving the native screen implementations, system chrome, Back handling, crash diagnostics and governed maintenance handoff. The authoritative Java compile and APK build passed and the APK was published. This build is intentionally plainer and exists primarily to isolate the crash source.

Important newly observed real-device bug: the current colour/theme controls are affecting the **Android phone/system theme/chrome rather than JANUS app-only colours**. This is incorrect behavior and must be fixed before further visual polish.

The menus are now usable enough to continue development from within the app.

## Active release scope

Android remains the active release target. Windows and iOS remain deferred.

## Next engineering task

**Next session starts with Android UI rebuild and the newly exposed theme bug.**

Priority order:

1. Fix colour/theme settings so they modify JANUS app appearance only and never alter the host Android phone theme/system appearance.
2. Rework the Android UI for readability, clarity and simpler navigation.
3. Move JANUS interaction surfaces away from native Android control styling/layout assumptions wherever practical so JANUS controls and Android/system controls can coexist safely.
4. Ensure both sets of controls/buttons remain usable with no JANUS element hidden behind, overlapped by, or confused with system/native Android buttons.
5. Replace fragile runtime view-tree decoration/injection patterns with explicit screen-owned layouts and deterministic rendering.
6. Preserve safe areas, predictive/system Back behavior, accessibility, system chrome compatibility and existing functional menus while doing the rebuild.
7. Re-test Cores, Memory, Settings, Stream, Messages, Observe and Options on the real Samsung device after each major UI step.
8. If any detail screen still closes in the stability path, expose the stored `JanusClientDiagnostics` crash report directly in-app with copy/share support and fix from the exact stack trace rather than further speculative UI changes.

The earlier broader **Diagnostic System v2 — behavioral proof phase** remains required after the Android UI is stable. It must still prove the 22-core recursive architecture, peer exchange/quiescence, sleep/wake behavior, memory behavior, seven -> Left/Right -> Front -> Interface routing, observer evidence, zero background model-call count, and append-only maintenance behavior.

Do not resume cosmetic polishing on top of the current global-layout injection stack. The next UI pass should simplify ownership and rendering first.
