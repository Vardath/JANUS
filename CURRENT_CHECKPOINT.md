# JANUS current checkpoint

**Current authoritative continuation:** `JANUS_CONSCIOUS_STREAM_MEMORY_CYCLE_CHECKPOINT_20260825.md`

**Current Android continuation:** Android v1.11 full-interface colour patch + human-readable telemetry baseline (PR #51, merge `b97829d4c6ec5ff427bb8783c8b9316c28f8d6e1`)

**Current project status:** `JANUS_PROJECT_STATUS_20260825.md`

**Mandatory maintenance runbook:** `MAINTENANCE_PROCESS.md`

**Branding/legal release plan:** `BRANDING_AND_NAME_RELEASE_PLAN.md` — preferred future public name is **JANUS 137**, but no broad rename should occur until the legal-release/name-clearance gate is performed.

Updated: 2026-08-28

## Critical architecture rules

Every one of the **22 top-level cores** is itself a complete JANUS-capable core: 11 local/Android + 11 global/server. Each contains all seven internal JANUS/Fano faculties. Outer role names are dispositions, not deleted faculties.

Every user event is registered to all cores. The only outward response route is:

`seven specialists -> Left + Right -> Front / stream of consciousness -> Interface -> user`

Interface receives Front only. Specialists and hemispheres may communicate internally but may not bypass Front into Interface.

Wake and rest alternate. Wake may perform bounded deterministic peer processing and reconsider retained interaction memory with zero model/API calls. Rest is passive: no scheduled recursive thought occurs, but state stays loaded and immediately responsive. Foreground user input can always rouse processing during rest.

Loop guards remain mandatory: identical per-core signatures become quiescent; unchanged whole-society retained state does not restart an all-peer wake pass; changed wake processing is bounded and terminates.

## Autonomous observation / continuing input

PR #52 is merged to `main` as `b97d4345c21f0379d81f2df6f868c7e91ccccccb`. It implements a governed digital-world observation layer so JANUS does not depend on user messages as its only source of new input.

- On every materially changed wake cycle, each of the 11 persistent global top-level cores may form its own bounded `curiosity_intent` after reviewing retained state, interaction memory and peer conclusions. Forming intentions is deterministic and makes zero model/API calls.
- A shared research gateway selects only a small subset of those intentions for paid outside observation. Duplicate/core-level curiosity therefore does not create 11 simultaneous paid searches.
- Search selection favors core-requested/relevant material, also explores adjacent material, and deliberately includes occasional exploratory/random observation so JANUS can encounter information that neither the user nor its current thread explicitly requested.
- Internet research includes a dedicated autonomous YouTube/video discovery mode alongside ordinary web/current-development/counterexample research.
- Successful external findings re-enter JANUS through the runtime typed `web` sensory hook and traverse the recursive society rather than jumping directly into Front or Interface.
- Findings begin as low-rung `trace` autonomous-research memories with source provenance. Existing consolidation/retrieval rules decide whether useful repeated material is promoted.
- The persistent global society can continue this process while no client is open, subject to host/server execution. Local Android cores remain subject to Android execution/suspension limits; global findings return through selective federation when the client reconnects.
- Ambient microphone and camera capture remain disabled. Continuing observation currently means governed digital information acquisition plus explicit/user-selected senses, not covert physical-world recording.

### Research budget invariant

The default per-account research policy is owner-set and must remain unchanged unless the owner explicitly changes it:

- **US$20/month maximum planned web-research allowance** shared by autonomous and user-directed web research.
- **US$10/month autonomous/background target and ceiling** inside that total.
- The remaining allowance is reserved for user-directed research; autonomous research may not consume it.
- Both background and foreground web scopes pass through the same persistent cost ledger and monthly governor.
- Wake/review/peer processing does not consume the paid-search allowance.
- Provider pricing/token overhead must be checked against production billing; the application governor must stay conservative. The owner-set US$20 ceiling must not be raised without explicit owner instruction.

### PR #52 verification

The final source-bearing implementation passed the clean server-v2 test/proof/diagnostic, recursive-core engine, conscious-stream cycle, Android maintenance checks and full Android APK build before merge. Production deployment and real unattended accumulation remain separate post-merge verification steps.

## Stream observer

The server `/desktop/stream-observe` endpoint and Android Stream surface expose bounded externalizable Front activity/state only. They may show Fano orientation, cycle/revision/peer/quiescence counters, integrated summaries, rousing and Front events. Never expose hidden chain-of-thought.

The former delayed reflective Stream injector is retired. Stream is a first-class explicitly owned top-level Android page. No private-field reflection, delayed attachment or live view-tree search should be restored.

## Android appearance, safe area and readability baseline

Android v1.11 remains the current device-validation baseline. `JanusTheme` owns JANUS app surfaces; Android status/navigation bars remain device-owned. Accent choices tint JANUS-owned backgrounds, cards, raised surfaces and bubbles while retaining high contrast. Observe/Stream/Cores/Memory present human-readable summaries before technical details. Explicit screen/component ownership remains mandatory; do not restore global-layout cosmetic injection stacks.

The authoritative Android filename remains `JANUS-Android-v1.11-FULL-REBUILD.apk`. PR #52 was server-only, so no Android update is required specifically for continuing digital observation.

## Maintenance request persistence

JANUS-generated maintenance/capability observations remain append-only and governed. JANUS may propose maintenance but does not authorize itself to edit code, install packages, change models/APIs or deploy itself.

## Active release scope

Android remains the active release target. Windows and iOS remain deferred.

## End-of-day handoff — 2026-08-25

Owner requested that development stop here for the day. Tomorrow, perform a fresh repository-wide review before changing code, inspect what genuinely remains, and then focus on **fine polishing and release blockers rather than architectural expansion**, targeting an Android release by the end of this week if validation supports it.

Tomorrow's first pass should cover: live Render revision/deployment of PR #52; evidence that unattended autonomous observations are accumulating inside the US$20/month / US$10 autonomous budget policy; Samsung v1.11 navigation/crash stability and theme/readability behavior; Diagnostic System v2 behavioral proof; authentication/release-signing/OAuth readiness; production configuration and secrets; privacy/security/release documentation; **JANUS 137 name clearance and controlled public-brand rename planning**; and any remaining Play-release packaging requirements. Do not call the build release-ready merely because CI is green—distinguish repository/CI proof, live-server proof and physical-device proof.

Preserve the current feature scope unless a demonstrated release blocker requires a change. The immediate objective is a stable, understandable, bounded-cost JANUS release candidate, followed by polish rather than another architecture rewrite.
