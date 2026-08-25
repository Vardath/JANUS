# JANUS current checkpoint

**Current authoritative continuation:** `JANUS_CONSCIOUS_STREAM_MEMORY_CYCLE_CHECKPOINT_20260825.md`

**Current Android continuation:** `JANUS_ANDROID_V110_UI_REBUILD_CHECKPOINT_20260825.md`

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

The former Android Stream activation layer used delayed view-tree searching and private-field reflection. v1.09 disabled that injection path during crash isolation. The replacement `JanusStreamScreen` is now an explicit screen-owned renderer with dependencies supplied by its host; it does not search or rewrite the live view tree and does not use reflection. It still needs direct native navigation integration before the Stream migration is complete.

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

The real-device crash affecting several detail screens persisted after earlier navigation/surface-reset changes. Investigation identified a plausible shared risk: multiple independent Android `OnGlobalLayoutListener`/UI-polish layers were walking and sometimes modifying the same live view hierarchy while detail screens were being laid out.

A stability-first v1.09 build therefore disabled competing cosmetic/runtime view-tree injection layers while preserving native screens, Android Back handling, crash diagnostics and governed maintenance handoff. The authoritative Java compile and APK build passed. This build was intentionally plainer and existed primarily to isolate the crash source.

### Android v1.10 app-only theme isolation — completed

The theme bug exposed by real-device testing has now been fixed in PR #45, merge `edb3f1f5b00153da0f572cff54057fb16f37c058`.

- JANUS `theme_mode` and `accent` remain application-owned appearance settings.
- They no longer recolour Android status/navigation bars.
- `JanusSystemChrome` follows only the device's own light/dark configuration for system-bar icon contrast.
- The authoritative APK build, UI-hardening, RC-readiness, auth, protocol, recursive-core and maintenance gates passed on the PR head before merge.

Two older Android gates remain useful signals rather than reasons to restore unsafe behavior: Stream and localization still expected runtime injection layers that v1.09 deliberately stopped installing. Those surfaces must be migrated to explicit screen/component ownership.

The new `JanusStreamScreen` begins that migration and is recorded in `JANUS_ANDROID_V110_UI_REBUILD_CHECKPOINT_20260825.md`.

## Active release scope

Android remains the active release target. Windows and iOS remain deferred.

## Next engineering task

**Continue the Android UI rebuild from explicit ownership, not from the old polish/injection stack.**

Priority order:

1. Wire `JanusStreamScreen` into first-class native navigation/page routing without reflection, delayed attachment or live view-tree search.
2. Move localization from the disabled global UI-localization injector into deterministic screen/component ownership while preserving the translation catalogue and English fallback.
3. Replace hard-coded visible build labels such as `Options · v1.09 (109)` with `BuildConfig` or one authoritative version helper.
4. Rework the Android UI for readability, clarity and simpler navigation.
5. Move JANUS interaction surfaces away from fragile native-control styling/layout assumptions wherever practical so JANUS controls and Android/system controls can coexist safely.
6. Ensure no JANUS element is hidden behind, overlapped by or confused with system navigation/buttons, predictive-back affordances, status/navigation bars, keyboards or accessibility overlays.
7. Preserve safe areas, predictive/system Back behavior, accessibility, Chat history, Messages, Observe, diagnostics, maintenance governance and existing functional menus.
8. Re-test Cores, Memory, Settings, Stream, Messages, Observe and Options on the real Samsung device after each major UI step.
9. If any detail screen still closes, expose the stored `JanusClientDiagnostics` crash report directly in-app with copy/share support and fix from the exact stack trace rather than further speculative UI changes.

The broader **Diagnostic System v2 — behavioral proof phase** remains required after the Android UI is stable. It must still prove the 22-core recursive architecture, peer exchange/quiescence, sleep/wake behavior, memory behavior, seven -> Left/Right -> Front -> Interface routing, observer evidence, zero background model-call count and append-only maintenance behavior.

Do not resume cosmetic polishing on top of the former global-layout injection stack. Screen ownership and deterministic rendering are now the UI baseline.
