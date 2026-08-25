# JANUS current checkpoint

**Current authoritative continuation:** `JANUS_CONSCIOUS_STREAM_MEMORY_CYCLE_CHECKPOINT_20260825.md`

**Current Android continuation:** `JANUS_ANDROID_V110_SAFEAREA_READABILITY_CHECKPOINT_20260825.md`

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

## Android appearance, safe area and readability baseline

The v1.09 stability shell disabled competing cosmetic/runtime view-tree injection layers after real-device crashes in detail screens suggested multiple layout listeners were mutating the same hierarchy during layout.

PR #45, merge `edb3f1f5b00153da0f572cff54057fb16f37c058`, completed v1.10 app-only theme isolation:

- JANUS `theme_mode` and `accent` remain app-owned appearance settings.
- They no longer recolour Android status/navigation bars.
- `JanusSystemChrome` follows only the device's own light/dark configuration for system-bar icon contrast.

PR #49, merge `23553c5683e50e37f1a963237de1aabc4b231675`, completed the next safe-area/readability pass:

- `JanusSafeArea` applies system-bar, display-cutout and IME insets directly to each authored root; it does not walk the live hierarchy or use global-layout listeners.
- Authentication and signed-in app roots opt into safe-area handling when created.
- `JanusBuildInfo` now supplies visible Android version/build identity from `BuildConfig.VERSION_NAME` and `BuildConfig.VERSION_CODE`; the Options title is no longer hard-coded to a release number.
- The five top-level native pages use a horizontally scrollable navigation surface with readable minimum tab widths rather than compressing all five labels into a narrow row.
- Stable Chat, Messages and Observe headings are localized explicitly at creation time; conversation bodies remain untouched.
- The safe-area/readability, authoritative APK, RC-readiness, localization, Stream-owner, conscious-stream, recursive-core, UI-hardening, protocol, maintenance and clean-server gates all passed before merge.

The safe UI baseline is now **explicit screen/component ownership and deterministic rendering**. Do not restore the former global-layout polish/injection stack merely to regain cosmetics.

## Device-validation handoff

The authoritative v1.10 Android build for the next real-device test is `JANUS-Android-v1.10-FULL-REBUILD.apk`, published on the `apk-download` branch. This is the build to install before reporting any remaining Cores, Memory, Settings, Stream, Messages, Observe, Options, keyboard or Back/navigation behavior. Do not diagnose an older installed APK as the current v1.10 baseline.

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

The next concrete phase is **real-device validation of the explicit-owner v1.10 UI**.

1. Test Chat, Messages, Observe, Stream, Options, Cores, Memory and Settings on the real Samsung device.
2. Open and dismiss the keyboard in Chat and authentication flows and confirm content/navigation remain above system/IME insets.
3. Check status/navigation bars, gesture navigation, predictive Back and accessibility/text scaling for overlap or inaccessible controls.
4. Confirm JANUS theme/accent changes stay app-local and do not recolour the phone/system theme.
5. Confirm the horizontally scrollable five-page navigation remains readable and every page is reachable.
6. If any detail screen still closes, expose/use the stored `JanusClientDiagnostics` crash report directly in-app with copy/share support and fix from the exact stack trace rather than speculative layout changes.
7. Continue explicit shell localization/readability cleanup only after the device path is stable.

The broader **Diagnostic System v2 behavioral proof phase** remains required after the Android UI is stable. It must prove the 22-core recursive architecture, peer exchange/quiescence, sleep/wake behavior, memory behavior, seven -> Left/Right -> Front -> Interface routing, observer evidence, zero background model-call count and append-only maintenance behavior.
