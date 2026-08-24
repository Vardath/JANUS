# JANUS Android RC1 diagnostic checkpoint — 2026-08-25

## Status
This file is the authoritative next-session checkpoint for the Android-first release effort.

It supersedes the old stopping-state language at the end of `JANUS_137_SENSORY_IMPLEMENTATION_PLAN.md` that described the 1-3-7 migration as only Stage 0 / branch work. The 1-3-7 sensory architecture and subsequent Android hardening are now merged into `main`.

Windows and iOS work is intentionally deferred until the Android version is ready for release and its setup/release process is understood end-to-end.

## Current product state
Android currently has:
- two independent 11-core societies: 11 local + 11 global;
- canonical conceptual topology 1|3|7 and mechanical flow 7 subconscious -> 2 hemispheres -> Front -> Interface;
- seven preserved specialist identities with Fano/E-V-P semantics: Evidence, Safety, Counterpoint, Context, Logic, Novelty, Memory;
- Left = logic/constraint/discrimination; Right = imagination/association/expansion;
- Front = bounded appraisal/intention; Interface = presentation/action selection;
- local/global selective sensory federation without overwrite;
- typed senses for text, image, audio, file/document, web/research, memory, runtime, peer and action result;
- foreground-only push-to-talk speech recognition using device/system recognition, with no ambient listener;
- audio-file transcription path with account-bound caching and governance;
- broad Android locale catalogue for JANUS conversation/research and speech;
- curated high-frequency native-shell translations for major language/script groups with English fallback;
- account-bound local-state isolation on sign-out/account switch;
- transient/offline `/auth/me` handling that preserves a valid cached local identity rather than spuriously logging out;
- bounded offline retry workers;
- notification-denial-safe background behavior;
- Android backup disabled for JANUS session/local continuity data;
- release-signing configuration path using external secrets/keystore;
- RC1, UI-hardening, protocol, maintenance, localization and APK build gates.

## What the latest real-device diagnostic taught us
A user-requested full diagnostic produced a very large wall of diagnostic prose inside the Chat surface. The content indicates that the major architecture is present and substantially healthier than earlier builds, but the presentation and verification model are now the weak point.

This changes the release plan. The next priority is not another broad feature expansion. It is to make diagnostics trustworthy, readable and useful for Android RC testing.

## New immediate priority: Diagnostic System v2

### Goal
Turn diagnostics from a long self-report in Chat into a structured verification system that distinguishes what is actually proven from what is inferred, unverified or only architecturally present.

### Required diagnostic states
Every diagnostic check must resolve to one of:
- PASS — directly verified by current runtime evidence;
- WARN — working/likely working but with a meaningful issue or degraded condition;
- FAIL — directly verified failure;
- UNVERIFIED — architecture/configuration exists but current runtime evidence is insufficient;
- NOT APPLICABLE — deliberately unavailable or disabled for the current platform/configuration.

A positive architectural claim must not be reported as PASS solely because a class, string, route or configuration key exists.

### Diagnostic categories
The diagnostic engine/report should separate at least:
1. Architecture health
   - exactly 11 canonical local cores;
   - exactly 11 canonical global cores where server state is available;
   - all seven subconscious roles present;
   - both hemispheres receive the intended field;
   - Front and Interface are canonical;
   - legacy `consensus` is compatibility-only and not a twelfth persisted core.
2. Local runtime health
   - local scheduler alive;
   - cycle progress observed;
   - persistence readable/writable;
   - Front/Interface appraisal bounded;
   - no runaway duplicate background work.
3. Global/server health
   - production endpoint reachable;
   - authenticated session accepted;
   - core sync succeeds;
   - global feedback returns through bounded peer/sensory path;
   - distinguish repository/CI health from live Render deployment health.
4. Memory/continuity health
   - account binding;
   - local memory persistence;
   - global/account memory retrieval;
   - no cross-account local leakage;
   - upgrade persistence marker intact.
5. Sensory/capability health
   - text;
   - files/documents;
   - images/vision;
   - web/research;
   - audio attachment understanding;
   - push-to-talk recognition availability/permission state;
   - action-result sensing.
6. Privacy/security health
   - ambient microphone capture disabled;
   - camera capture disabled unless explicitly implemented later;
   - authentication payloads excluded from sensory telemetry;
   - backup disabled;
   - account isolation state;
   - token/session handling status.
7. Background/battery/network health
   - unique retry workers;
   - notification permission condition;
   - offline queue count;
   - connectivity/reconnect state;
   - recent worker failures/retries;
   - no claim of continuous execution while Android has suspended/killed the process.
8. Localization/voice health
   - selected JANUS language;
   - speech locale;
   - recognizer availability/on-device/fallback state;
   - translation-shell coverage vs English fallback;
   - RTL mode where applicable.
9. Release health
   - app version/build identity;
   - debug vs release signing state;
   - server build identity if verifiable;
   - required RC gates last-known status;
   - live production deployment separately marked VERIFIED or UNVERIFIED.

### Presentation requirements
A full diagnostic must no longer dump the entire report inline into Chat.

Chat should show a compact executive result, approximately:

`Overall: HEALTHY / DEGRADED / ATTENTION NEEDED / FAILED`

plus counts such as:
`31 PASS · 4 WARN · 2 UNVERIFIED · 0 FAIL`

and the top 3-5 attention items.

Then expose:
- `View full diagnostic`
- `Copy report`
- `Share to ChatGPT/Supervisor`

The full report should be its own readable native surface with sections, severity/status markers and expandable technical evidence.

Do not expose private hidden chain-of-thought. Show only bounded externalizable diagnostic evidence, state, counters, timestamps, error codes and summaries.

### Diagnostic trust rules
- Runtime evidence outranks static architecture presence.
- Live server evidence must be distinct from GitHub CI/repository evidence.
- A failed connectivity check must not be interpreted as invalid authentication unless the server actually returns an authentication rejection.
- `UNVERIFIED` is preferable to a false PASS.
- Diagnostics should state the age/timestamp of evidence where practical.
- Self-reported JANUS prose is not itself evidence that a subsystem works.
- Diagnostic checks should be deterministic/low-cost and should not invoke paid model calls merely to test themselves.

## Android RC1 plan — adjusted order

### Phase A — Diagnostic System v2 [NEXT]
1. Audit every current diagnostic check and identify static/shallow/self-reported checks.
2. Introduce PASS/WARN/FAIL/UNVERIFIED/NOT-APPLICABLE result schema.
3. Add category summaries and an overall health posture.
4. Add evidence/timestamp/source fields.
5. Build dedicated native full-diagnostic screen.
6. Make Chat diagnostic response concise with a `View full diagnostic` action.
7. Preserve Copy/Share-to-Supervisor handoff.
8. Add CI regression gates for diagnostic schema and no giant Chat dump.

### Phase B — Android real-device soak
After Diagnostic v2 is available, test the actual device rather than adding major architecture:
- update/install and reopen without losing login/local continuity;
- force-stop/kill/reopen;
- offline startup;
- offline send -> reconnect -> exactly-once delivery behavior;
- Render wake/transient failure without spurious logout;
- push-to-talk grant/deny/retry and dictation into an existing draft;
- language switching English -> Spanish/Japanese -> Arabic/RTL -> English;
- file/image/audio attachment handling;
- image generation/research;
- notification allowed/denied;
- local/global sync after disconnect/reconnect;
- sign out -> second account -> prove first account local state absent;
- sign back into first account -> prove global/account continuity returns without inheriting second-account local state;
- extended background/sleep/wake use looking for spam, duplicate thought/messages, battery drain, worker storms, crashes or state corruption.

Use Diagnostic v2 before/after these scenarios to capture comparable evidence.

### Phase C — fix soak-test failures only
Prioritize:
1. crashes/data loss/privacy/account leakage;
2. authentication/session/reconnect failures;
3. duplicate delivery/background/battery problems;
4. core/sync continuity failures;
5. voice/permission failures;
6. localization/RTL/readability problems;
7. cosmetic debt.

Do not add speculative major features during this phase unless required to fix a release blocker.

Known low-priority cosmetic debt: some legacy UI/status text may still refer to `Consensus` even though Front is canonical. Do not risk a large MainActivity rewrite solely for that label before soak unless it causes real confusion or incorrect behavior.

### Phase D — release signing transition
Before public release:
- create/secure the permanent Android release keystore;
- configure GitHub/CI release secrets without committing keys/passwords;
- deliberately plan migration from the current debug-signed test APK because Android will not accept a differently signed public build as an in-place update;
- bump versionCode/versionName only when the release candidate is intentionally cut;
- produce signed APK for direct testing and AAB for Play Store path;
- test clean install and intended upgrade path.

### Phase E — production verification
Before calling Android released:
- verify the live Render server is actually running the intended current server-v2 revision;
- verify production auth, chat, sync, files/images/research/audio against the release-signed build;
- distinguish live-deployment evidence from repository CI;
- verify graceful degradation when the server is sleeping/unreachable;
- verify maintenance/Supervisor handoff remains owner-governed.

## Deferred until Android release process is understood
- Windows local/client release work;
- iOS local/client release work;
- cross-platform spoken-reply parity;
- premium/cloud voice quality mode;
- ambient microphone/camera sensing;
- broad new architectural features unrelated to Android RC blockers.

## Next-session instruction
Resume with **Diagnostic System v2, Phase A**.

Do not begin by redesigning the 1-3-7 architecture again. Treat the current 11-local + 11-global Fano/sensory architecture as the active implementation unless a concrete diagnostic or soak-test failure disproves part of it.

Start by reviewing the current Android/server diagnostic code and the screenshot-driven problem: full diagnostics are too verbose in Chat and mix architecture claims with runtime verification. Refactor diagnostics into structured evidence-backed checks and a dedicated report surface, then build/test the APK before proceeding to the device soak.
