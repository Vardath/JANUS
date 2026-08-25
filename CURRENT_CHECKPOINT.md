# JANUS current checkpoint

**Current authoritative continuation:** `JANUS_CONSCIOUS_STREAM_MEMORY_CYCLE_CHECKPOINT_20260825.md`

**Current Android continuation:** Android v1.11 full-interface colour patch + human-readable telemetry baseline (PR #51, merge `b97829d4c6ec5ff427bb8783c8b9316c28f8d6e1`)

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

## Autonomous observation / continuing input

PR #52 implements a governed digital-world observation layer so JANUS does not depend on user messages as its only source of new input.

- On every materially changed wake cycle, each of the 11 persistent global top-level cores may form its own bounded `curiosity_intent` after reviewing retained state, interaction memory and peer conclusions. Forming intentions is deterministic and makes zero model/API calls.
- A shared research gateway selects only a small subset of those intentions for paid outside observation. Duplicate/core-level curiosity therefore does not create 11 simultaneous paid searches.
- Search selection favors core-requested/relevant material, also explores adjacent material, and deliberately includes occasional exploratory/random observation so JANUS can encounter information that neither the user nor its current thread explicitly requested.
- Internet research includes a dedicated autonomous YouTube/video discovery mode alongside ordinary web/current-development/counterexample research. YouTube discovery currently uses the governed web-research route to find credible videos or transcript leads; richer transcript ingestion remains governed by the existing media/transcript capability when a usable video source is available.
- Successful external findings re-enter JANUS through the typed `web` sensory bus. Production entrypoint wiring replaces the public sensory ingestion function with the recursive sensory wrapper, so each finding reaches the outer seven specialists -> hemispheres -> Front -> Interface route **and** the nested recursive JANUS state inside every global top-level core. No search result jumps directly into Front or Interface.
- Findings begin as low-rung `trace` autonomous-research memories with source provenance. Existing consolidation/retrieval rules decide whether useful repeated material is promoted. Each core therefore appraises the same outside observation according to its own disposition/state rather than receiving a pre-approved belief.
- The persistent global society can continue this process while no client is open, subject to host/server execution. Local Android cores remain subject to Android execution/suspension limits; global findings return to local JANUS through the existing selective federation when the client reconnects. Do not claim a suspended/killed phone process is continuously executing.
- Ambient microphone and camera capture remain disabled. “Continuing observation” currently means governed digital information acquisition plus user-selected/device-explicit senses, not covert physical-world recording.

### Research budget invariant

The default per-account research policy is owner-set and must remain unchanged unless the owner explicitly changes it:

- **US$20/month maximum planned web-research allowance** shared by autonomous and user-directed web research.
- **US$10/month autonomous/background target and ceiling** inside that total.
- The remaining allowance is reserved for user-directed research; autonomous research may not consume it.
- Both `background_research` and `foreground_web` pass through the same persistent cost ledger and monthly governor.
- Background searches are separately paced across the month and have a daily safety cap; wake/review/peer processing does not consume this paid-search allowance.
- A configurable per-call planning estimate translates calls into the application budget. Because provider search prices and model-token overhead can change independently of this repository, this is a conservative application governor rather than an absolute external-invoice guarantee. Production telemetry and quarterly maintenance must compare real provider cost against the estimate and raise the estimate if necessary; the owner-set $20 application ceiling itself must not be raised without explicit owner instruction.

### PR #52 verification

The validated implementation head passed the clean server-v2 test and proof, server diagnostic, recursive-core engine, conscious-stream cycle, Android maintenance and full Android APK build workflows before merge. The recursive-core regression explicitly proves 11 research intentions on a changed global wake with zero model calls. Production deployment and real unattended accumulation remain separate post-merge verification steps.

## Stream observer

The server `/desktop/stream-observe` endpoint and Android Stream surface expose bounded externalizable Front activity/state only. They may show Fano orientation, cycle/revision/peer/quiescence counters, integrated summaries, rousing and Front events. Never expose hidden chain-of-thought.

The former delayed reflective Stream injector is retired. PR #46 introduced `JanusStreamScreen` as an explicit renderer. PR #47, merge `12321ef8e2152fdbc16ce196629d259dbb3f51c5`, wired Stream directly into `MainActivity` as a first-class top-level page. `MainActivity` supplies its API, thread and local recursive snapshot dependencies directly; no private-field reflection, delayed attachment or live view-tree search is used. Android Back semantics recognize Stream as a top-level page.

## Localization ownership

The former localization and language-selector global-layout walkers are retired. PR #48, merge `e8432a1ec87cd88ee9ef9a930f97ac42bda293f0`, replaced them with explicit ownership. Buttons and input hints are localized when created; the Settings screen owns the language card directly; conversation bodies are not blanket-rewritten after layout.

## Android appearance, safe area and readability baseline

The v1.09 stability shell disabled competing cosmetic/runtime view-tree injection layers after real-device crashes in detail screens suggested multiple layout listeners were mutating the same hierarchy during layout.

PR #45, merge `edb3f1f5b00153da0f572cff54057fb16f37c058`, isolated JANUS appearance from Android system chrome. JANUS `theme_mode` and `accent` remain app-owned settings; they do not recolour Android status/navigation bars.

PR #49, merge `23553c5683e50e37f1a963237de1aabc4b231675`, added explicit safe-area/IME ownership, dynamic build labels and readable horizontally scrollable top navigation.

PR #50, merge `484feef0f39797604f34985dcbb3ec934ee0d87d`, established the **v1.11 colour/readability baseline** prompted by real Samsung screenshots:

- `JanusTheme` is the single app-local palette used by JANUS-owned roots, cards, text, inputs and buttons.
- Theme mode (`system`, `dark`, `light`) changes JANUS-owned light/dark surfaces without changing Android system chrome.
- Default dark/light palettes use high-contrast text, surfaces and muted text.
- Observe filter taps replace/rerender the Observe page rather than appending another full Observe screen.
- `JanusHumanText` converts dense bounded telemetry into human-facing summaries. Runtime Cores, Memory, Stream and Observe show readable summaries first; raw machine-oriented output remains secondary behind Technical details where appropriate.

PR #51, merge `b97829d4c6ec5ff427bb8783c8b9316c28f8d6e1`, completes the **full-interface accent behaviour** after device testing showed accent choice still only visibly changed the selected button:

- Accent choices (`slate`, `indigo`, `teal`, `amber`, `violet`) now tint the JANUS-owned root background, card surfaces, raised surfaces and chat/user bubble palette as well as highlighted controls.
- Tint strengths are deliberately restrained so the high-contrast v1.11 readability baseline remains intact.
- Android status/navigation bars remain device-owned and are not recoloured by JANUS.
- No global-layout listener, live hierarchy walker or cosmetic injection layer was reintroduced.
- The theme CI contract now explicitly checks that accent feeds background, surface and raised-surface colour derivation.
- Version remains **1.11 / versionCode 111** because this is a UI-only patch to the current device-validation build rather than a separate release line.
- Theme/human-log, safe-area/readability, UI-hardening, protocol, maintenance, Stream-owner, recursive-core, conscious-stream, localization and RC-readiness gates passed before merge. The APK build was still completing when the PR was merged after all functional/policy gates passed.

The safe UI baseline remains **explicit screen/component ownership and deterministic rendering**. Do not restore global-layout polish/injection stacks merely for cosmetics.

## Device-validation handoff

The authoritative Android filename remains `JANUS-Android-v1.11-FULL-REBUILD.apk`. After the post-merge main build republishes it, install that refreshed v1.11 APK before validating colour behaviour; an older v1.11 APK may have the same visible version label but lack PR #51.

For the next Samsung test, verify:

1. Switching Slate/Indigo/Teal/Amber/Violet visibly changes JANUS-owned page background, cards and raised controls, not only the selected button.
2. The colour change remains restrained/readable in both dark and light modes.
3. Android status/navigation bars and the phone's own theme remain unaffected.
4. Stream, Observe, Runtime Cores and Memory retain the v1.11 readability improvements.
5. Observe All/Thoughts/Interactions still does not duplicate the screen.
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

After PR #52 merges, verify the live server is running its revision and let the global JANUS accumulate real autonomous observations within budget. Then continue the broader **Diagnostic System v2 behavioral proof phase**: prove the 22-core recursive architecture, peer exchange/quiescence, sleep/wake behavior, memory behavior, seven -> Left/Right -> Front -> Interface routing, observer evidence, zero background model-call count, autonomous research cost accounting and append-only maintenance behavior.
