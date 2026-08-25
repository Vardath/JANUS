# JANUS current checkpoint

**Current authoritative continuation:** `JANUS_CONSCIOUS_STREAM_MEMORY_CYCLE_CHECKPOINT_20260825.md`

**Current Android continuation:** Android v1.11 app-local colour + human-readable telemetry pass (PR #50, merge `484feef0f39797604f34985dcbb3ec934ee0d87d`)

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

The former delayed reflective Stream injector is retired. PR #46 introduced `JanusStreamScreen` as an explicit renderer. PR #47, merge `12321ef8e2152fdbc16ce196629d259dbb3f51c5`, wired Stream directly into `MainActivity` as a first-class top-level page. `MainActivity` supplies its API, thread and local recursive snapshot dependencies directly; no private-field reflection, delayed attachment or live view-tree search is used. Android Back semantics recognize Stream as a top-level page.

## Localization ownership

The former localization and language-selector global-layout walkers are retired. PR #48, merge `e8432a1ec87cd88ee9ef9a930f97ac42bda293f0`, replaced them with explicit ownership. Buttons and input hints are localized when created; the Settings screen owns the language card directly; conversation bodies are not blanket-rewritten after layout.

## Android appearance, safe area and readability baseline

The v1.09 stability shell disabled competing cosmetic/runtime view-tree injection layers after real-device crashes in detail screens suggested multiple layout listeners were mutating the same hierarchy during layout.

PR #45, merge `edb3f1f5b00153da0f572cff54057fb16f37c058`, isolated JANUS appearance from Android system chrome. JANUS `theme_mode` and `accent` remain app-owned settings; they do not recolour Android status/navigation bars.

PR #49, merge `23553c5683e50e37f1a963237de1aabc4b231675`, added explicit safe-area/IME ownership, dynamic build labels and readable horizontally scrollable top navigation.

PR #50, merge `484feef0f39797604f34985dcbb3ec934ee0d87d`, is the **v1.11 colour/readability pass** prompted by real Samsung screenshots:

- `JanusTheme` is now the single app-local palette used by JANUS-owned roots, cards, text, inputs and buttons.
- Theme mode (`system`, `dark`, `light`) and accent choices (`slate`, `indigo`, `teal`, `amber`, `violet`) now visibly repaint JANUS UI rather than merely saving preferences.
- Theme code contains no Android status-bar/navigation-bar recolouring APIs; Android system chrome remains device-owned.
- Default dark/light palettes use high-contrast text, surfaces and muted text. The previous Stream dark-text-on-dark-blue failure is removed.
- Selected top-level navigation and selected Observe filters use the chosen accent; unselected controls remain neutral/readable.
- Observe filter taps now replace/rerender the Observe page rather than appending another full Observe screen. This fixes the repeated Observe UI seen in device testing.
- `JanusHumanText` converts dense bounded telemetry into a human-facing summary. Runtime Cores, Memory, Stream and Observe show readable summaries first; raw machine-oriented output remains secondary behind Technical details where appropriate.
- Version is **1.11 / versionCode 111**.
- PR validation passed after stale v1.10 CI assertions were brought forward. The authoritative main-branch Java compile and APK assembly passed and the direct-download publish step succeeded.

The safe UI baseline remains **explicit screen/component ownership and deterministic rendering**. Do not restore global-layout polish/injection stacks merely for cosmetics.

## Device-validation handoff

The authoritative Android build is now `JANUS-Android-v1.11-FULL-REBUILD.apk`, published at `apk-download/downloads/JANUS-Android-v1.11-FULL-REBUILD.apk`. The published file was verified present after the successful main-branch build.

For the next Samsung test, verify:

1. Switching System/Dark/Light changes JANUS itself immediately after the screen rerenders/reopens but does not alter the phone's Android theme or system bar colours.
2. Slate/Indigo/Teal/Amber/Violet visibly change JANUS accents, especially selected navigation/filter controls.
3. Stream has readable foreground/background contrast.
4. Observe All/Thoughts/Interactions no longer duplicates the screen.
5. Runtime Cores and Memory are readable as summaries, with Technical details available for raw diagnostic data.
6. Messages/Observe/Stream/Cores/Memory remain stable during normal navigation and Back use.

## Maintenance request persistence

JANUS-generated maintenance/capability observations remain append-only and governed.

- Structured state: SQLite `v2_capability_requests`.
- Chronological persistent ledger: `janus_maintenance_requests.jsonl`.
- Supervisor decisions: `server_v2/supervisor_decisions.json`.
- Reconciliation removes only implemented/disapproved entries; deferred, pending, repeated and unresolved entries remain.
- Mandatory procedure: `MAINTENANCE_PROCESS.md`.

JANUS may propose maintenance but does not authorize itself to edit code, install packages, change models/APIs or deploy itself.

## Active release scope

Android remains the active release target. Windows and iOS remain deferred.

## Next engineering task

The immediate next task is **real-device validation of v1.11 colours and human-readable telemetry** using the published v1.11 APK. Fix any remaining device-specific contrast, theme refresh or log-layout defect from exact device evidence. If a detail screen closes, use `JanusClientDiagnostics` rather than speculative layout changes.

After Android UI stability, continue the broader **Diagnostic System v2 behavioral proof phase**: prove the 22-core recursive architecture, peer exchange/quiescence, sleep/wake behavior, memory behavior, seven -> Left/Right -> Front -> Interface routing, observer evidence, zero background model-call count and append-only maintenance behavior.
