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

Wake and rest alternate. Wake may perform bounded deterministic peer processing and reconsider retained interaction memory with zero model/API calls. Rest is passive: no scheduled recursive thought occurs, but state stays loaded and immediately responsive. Foreground user input can always rouse processing during rest.

Loop guards remain mandatory: identical per-core signatures become quiescent; unchanged whole-society retained state does not restart an all-peer wake pass; changed wake processing is bounded and terminates.

## Stream observer

The server `/desktop/stream-observe` endpoint and Android Stream surface expose bounded externalizable Front activity/state only. They may show Fano orientation, cycle/revision/peer/quiescence counters, integrated summaries, rousing and Front events. Never expose hidden chain-of-thought.

The former delayed reflective Stream injector is retired. PR #46 introduced `JanusStreamScreen` as an explicit renderer. PR #47, merge `12321ef8e2152fdbc16ce196629d259dbb3f51c5`, wired Stream directly into `MainActivity` as a first-class top-level page. `MainActivity` supplies its API, thread and local recursive snapshot dependencies directly; no private-field reflection, delayed attachment or live view-tree search is used. Android Back semantics now recognize Stream as a top-level page.

## Localization ownership

The former localization and language-selector global-layout walkers are retired. PR #48, merge `e8432a1ec87cd88ee9ef9a930f97ac42bda293f0`, replaced them with explicit ownership:

- `JanusUiLocalizationPolish` is now a deterministic helper, not an installer. Buttons and input hints are localized when MainActivity creates them.
- `JanusLanguagePolish.renderSettingsCard(...)` is called directly by the Settings screen; it no longer searches the live view hierarchy.
- Conversation bodies are not blanket-rewritten after layout.
- The curated translation catalogue and English fallback remain intact.
- Localization CI now forbids `OnGlobalLayoutListener` / `getViewTreeObserver` in both localization components.

The localization, Stream-owner, conscious-stream, UI-hardening, RC-readiness, recursive-core, protocol, maintenance, clean-server and authoritative APK build gates all passed on PR #48 before merge.

## Android appearance and stability baseline

The v1.09 stability shell disabled competing cosmetic/runtime view-tree injection layers after real-device crashes in detail screens suggested multiple layout listeners were mutating the same hierarchy during layout.

PR #45, merge `edb3f1f5b00153da0f572cff54057fb16f37c058`, completed v1.10 app-only theme isolation:

- JANUS `theme_mode` and `accent` remain app-owned appearance settings.
- They no longer recolour Android status/navigation bars.
- `JanusSystemChrome` follows only the device's own light/dark configuration for system-bar icon contrast.

The safe UI baseline is now **explicit screen/component ownership and deterministic rendering**. Do not restore the former global-layout polish/injection stack merely to regain cosmetics.

## Maintenance request persistence

JANUS-generated maintenance/capability observations remain append-only and governed.

- Structured state: SQLite `v2_capability_requests`.
- Chronological persistent ledger: `janus_maintenance_requests.jsonl`.
- Supervisor decisions: `server_v2/supervisor_decisions.json`.
- Reconciliation removes only implemented/disapproved entries; deferred, pending, repeated and unresolved entries remain.
- Mandatory procedure: `MAINTENANCE_PROCESS.md`.
- Procedure command: `python -m server_v2.maintenance_request_file instructions`.
- Reconciliation command: `python -m server_v2.maintenance_request_file reconcile`.

JANUS may propose maintenance but does not authorize itself to edit code, install packages, change models/APIs or deploy itself.

## Active release scope

Android remains the active release target. Windows and iOS remain deferred.

## Next engineering task

Continue the Android UI rebuild from the explicit-owner baseline.

1. Replace remaining hard-coded visible version/build labels with `BuildConfig` or one authoritative version helper.
2. Continue migrating static shell text to explicit localized rendering while leaving conversation/research/user content untouched.
3. Improve readability and navigation without reintroducing hierarchy walkers or competing runtime decorators.
4. Make safe-area/system-control coexistence explicit so JANUS content is not hidden by status/navigation bars, predictive Back, keyboards or accessibility overlays.
5. Re-test Cores, Memory, Settings, Stream, Messages, Observe and Options on the real Samsung device after each major UI step.
6. If any detail screen still closes, expose the stored `JanusClientDiagnostics` crash report directly in-app with copy/share support and fix from the exact stack trace rather than speculative UI changes.

The broader **Diagnostic System v2 behavioral proof phase** remains required after the Android UI is stable. It must prove the 22-core recursive architecture, peer exchange/quiescence, sleep/wake behavior, memory behavior, seven -> Left/Right -> Front -> Interface routing, observer evidence, zero background model-call count and append-only maintenance behavior.
