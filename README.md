# JANUS Global Core

JANUS is an experimental functional-metacognition/agency application with persistent local + global state. It does **not** claim phenomenal consciousness.

## Current architecture

Canonical cognitive topology: **11 cores arranged 7 → 2 → 1 → 1**.

- 7 specialists: Evidence, Logic, Counterpoint, Context, Memory, Safety, Novelty.
- 2 hemispheres: left synthesis and right synthesis.
- 1 Consensus core reconciles the hemispheres.
- 1 Interface core surfaces the result to Chat/Messages.

Ordinary routing is forward-only: specialists → assigned hemisphere → Consensus → Interface. Consensus/Interface output is not automatically recycled as a new topic. Remote/client summaries are compressed, tagged as feedback/grounding, and re-enter through specialist review rather than directly through Consensus.

Fano/JANUS state is operational rather than decorative: persistent d0–d7 orientations can influence attention, processing pressure and integration bias, while evidence remains grounded independently of Fano state.

## Current client/runtime status

**Android working line: v0.64.** The Aug 22 telemetry investigation verified two independent, functioning societies:

- the Android local 11-core runtime advances its own persistent wake/sleep, memory, Fano, routing and deterministic zero-API cycles;
- the Render/global 11-core runtime has a live background thread, persistent server state and independently advancing server cycle counters;
- authenticated device presence is visible server-side and is kept separate from server-core counters;
- local and global counters must never be substituted for one another.

Android v0.64 changes the Cores-screen server telemetry architecture: the native authenticated `/core-sync/exchange` heartbeat returns the authoritative server runtime snapshot, Android stores that successful heartbeat snapshot, and the WebView reads it through the native bridge. The Cores screen should display a waiting/error state when no authenticated snapshot exists rather than fabricating zero-cycle server cores.

The v0.64 Cores display still requires real-device verification before the long-running telemetry issue is considered closed. See `JANUS_PROJECT_MEMORY_2026-08-22.md` for the detailed checkpoint and regression lessons.

Windows and iOS remain development clients/CI artifacts where applicable; real Windows launch testing and Apple signing/TestFlight/device testing remain platform-specific validation steps.

The Android Messages path has been real-device tested end-to-end with a JANUS-originated test message. Autonomous useful unsolicited messaging is intentionally thresholded and remains an ongoing soak-test target rather than routine telemetry spam.

This repository is still a development/beta project. Account creation/login, OAuth, email recovery, platform builds and long-running background behaviour should be tested before public release.

## Accounts and privacy

Private Chat, Messages, Observe, Cores, Memory, Activity and Settings routes are bound to the authenticated JANUS account rather than a client-supplied profile name. Passwords are stored only as salted PBKDF2 hashes. Server session tokens are stored as hashes; supported native clients use OS-protected token storage where implemented.

Public authentication endpoints are rate-limited. Detailed deployment/schema diagnostics require the server administrative token. Temporary chat-delivery receipts and repetitive runtime snapshots have bounded retention; meaningful conversation/memory continuity data remains until account deletion.

Generated images and uploaded files use the same account-bound persistent file store. File bytes are not made public merely to display them in clients: Windows/iOS use authenticated binary download and Android uses an authenticated inline/base64 transport. The global storage auditor may review stale unpinned files under its configured retention policy.

See `/privacy` and `/terms` on the deployed service for the current legal-development pages.

## API/background cost policy

Deterministic local/server core cycles do not require external language-model calls. Paid background language reflection is **disabled by default** in production. User-triggered Chat may use the configured OpenAI model.

Stage-1 image generation is bounded separately. Explicit user image requests and rare explanation-helpful visuals can render under account/global caps and cache reuse. Background multi-core image generation, candidate render/review loops and autonomous visual deliberation remain disabled until deliberately enabled under a future revenue/cost policy.

Bounded web curiosity is a separate capability: JANUS may occasionally perform relevant, adjacent or unrelated learning searches under daily/mode caps and cooldowns. Self-regulation may request a relevant search when processing becomes starved of fresh grounding, but it cannot bypass those caps.

## File and image capabilities

The current feature stack adds authenticated file storage, autonomous retention auditing and bounded Stage-1 image generation. Generated images are reusable file artifacts and therefore share the same ownership, deletion and retention controls as other attachments.

Future work still includes richer document parsing/grounding, image/screenshot recognition, and eventually the revenue-gated multi-core visual deliberation system described in `DEFERRED_FEATURES.md` and `IMAGE_GENERATION_POLICY.md`.

## Render deployment

This repository includes a `render.yaml` Blueprint. Deployment uses the resilient `bootstrap:app` entrypoint. The historical base FastAPI module is reconstructed at build time from the checked-in `src/server.py.gz.b64.*` fragments via `tools/rebuild_server.py`; both Render and Docker use this same explicit step.

The Blueprint provides:

- one Starter web service;
- a 1 GB persistent disk mounted at `/data`;
- `JANUS_DB_PATH=/data/janus.sqlite3`;
- `/health` plus safe `/diagnostics/runtime-health` checks;
- automatic deployment from `main`;
- a generated `JANUS_ACCESS_TOKEN` for administrative endpoints.

Do not commit API keys, SMTP credentials, OAuth secrets, access tokens or private signing credentials.

## Reliability checks

GitHub Actions contains regression/build workflows for:

- Android APK builds and routing verification;
- authentication lifecycle/security tests;
- file ownership/retention and image-generation policy tests;
- forward-only routing and remote-feedback tests;
- operational Fano semantics and saturation-regulation checks;
- architecture/deployment contract checks;
- Windows client packaging;
- iOS simulator compilation.

The Android telemetry regression target is now explicit: a build must not show zero/unknown Server JANUS cores when the same authenticated account has a live heartbeat/server diagnostic showing an advancing server runtime. Critical telemetry should have one authoritative data path rather than competing WebView/native readers.

Before treating a build as released, verify the actual artifact/download branch rather than inferring success from a version bump or commit alone.
