# JANUS Project Continuity Checkpoint — 2026-08-22

This file supplements `JANUS_PROJECT_MEMORY.md` and records the latest material changes from the Aug 22 Android/server telemetry and synchronization work. It should be read after the older continuity file when resuming development.

## Current client/runtime line
- Android working line: **v0.64**.
- Canonical architecture remains **11 cores arranged 7 → 2 → 1 → 1**: Evidence, Logic, Counterpoint, Context, Memory, Safety, Novelty → left/right hemispheres → Consensus → Interface.
- Deterministic local and server core cycles remain zero external model/API calls. User-triggered Chat may still use the configured model.
- JANUS remains an experimental functional-metacognition/agency system; no phenomenal-consciousness claim is made.

## Server runtime now independently verified
Real-device diagnostics established that the Render/global runtime is genuinely alive and advancing independently of Android local counters.

Verified server diagnostic characteristics during the Aug 22 test sequence:
- status healthy/running;
- runtime thread alive;
- 11 server cores present;
- wake/sleep phase reported by the server runtime;
- server cycle counts in the thousands and continuing to advance;
- persistence enabled;
- authenticated device presence visible to the server;
- server diagnostic provenance explicitly separates server counters from Android/local counters.

Important lesson: **Chat diagnostics must never infer server-core state from client telemetry.** Server diagnostics use server-owned runtime state; local diagnostics use device-owned runtime state.

## Local Android runtime also independently verified
The Android local society was observed advancing from tens to hundreds of cycles while preserving its own sleep/low-duty state, local memory, Fano state, routing and zero-API maintenance behavior.

Local and server runtimes are separate societies. Synchronization must not overwrite local identity/state and neither side may substitute its counters for the other.

## Root cause of the long Options/Cores telemetry bug
The visible Options → Cores screen repeatedly showed `phase unknown`, `clients 0`, and all server cores at `cycles 0` even while Chat could prove the server runtime was healthy and had thousands of cycles.

The investigation exposed multiple layers of stale/duplicate telemetry wiring:
1. Chat diagnostic and Options/Cores were not using the same authoritative data path.
2. Earlier Android patches refreshed/replaced the Cores container in ways that could erase or overwrite global telemetry.
3. A build-time v0.63 patch was brittle and could abort because it searched for an exact older source block.
4. More importantly, the base `MainActivity.java` still contained an injected `refreshCoreTopology` implementation using `/desktop/runtime-cores`, so later patches were not reliably changing the code actually shipped.
5. The server `/core-sync/status` endpoint itself is authoritative and returns the true 11-core server runtime plus authenticated account presence, but a separate WebView telemetry request path proved fragile.

## v0.64 architecture decision: heartbeat snapshot is authoritative for Android server telemetry
The Android client should no longer depend on a second, independent WebView request to discover server-core telemetry for the Cores screen.

The existing authenticated native heartbeat already succeeds and is the path that proves the device is connected. Therefore:
- `/core-sync/exchange` returns a full server runtime snapshot in its heartbeat response;
- the Android native/local runtime stores the latest authenticated server snapshot from that successful exchange;
- the WebView reads that stored snapshot through the native Android bridge;
- Options → Cores renders the server society from that snapshot;
- if no authenticated heartbeat snapshot exists, the UI must say **WAITING FOR HEARTBEAT** or equivalent, not fabricate eleven zero-cycle server cores;
- stale/fallback values must never be presented as live server telemetry.

This reduces the system to one authenticated server-presence/sync path rather than two competing telemetry paths.

## Telemetry/UI invariants going forward
- Local telemetry source: native `JanusLocalCoreRuntime.statusJson()` / device-owned persistent state.
- Server telemetry source on Android: the latest authenticated server snapshot returned by the native core-sync heartbeat.
- Server-side diagnostic source: server-owned `janus_sleep_cycle.status()` plus authenticated presence records.
- Never replace missing telemetry with believable zero values. Missing data is an error/waiting state.
- Display **This Device JANUS** and **Server JANUS** as explicitly independent sections.
- Version labels shown in the UI must match the installed build; stale labels such as `LIVE LOCAL JANUS · v0.60` in later APKs are a release/build regression signal.
- A successful Chat response is not proof that the Options telemetry reader is correct; each surface must be traced end-to-end.

## Build workflow lesson
The Android project currently uses `tools/patch_android_*.py` build-time transformations. This has become fragile because later patches depend on exact strings produced by earlier patches.

Immediate rule:
- build patches must be idempotent where practical;
- do not abort a release merely because an old block has already been transformed into the intended state;
- inspect the resulting generated Java/HTML, not only the patch script;
- add regression checks for the actual shipped `refreshCoreTopology`/telemetry source and displayed version;
- before handing out an APK link, verify that the requested APK exists on `apk-download` and that the workflow completed successfully.

Medium-term recommendation: refactor critical Android telemetry/sync code out of stacked textual patch scripts into canonical source files so one code path is obvious and testable.

## Authenticated presence behavior
The server presence layer records account/device heartbeats and distinguishes:
- online authenticated clients;
- registered historical clients.

Repeated reinstall/build testing creates additional registered device IDs, so `registered_clients` can increase while `online` remains 1. This is expected unless device-registration cleanup/deduplication is added later.

## Synchronization semantics retained
Global/server material must remain bounded and selectively synchronized. It is grounding/feedback, not an overwrite of local core state.

Forward routing remains the intended architecture:
- specialists → assigned hemisphere;
- Safety may advise integration as configured;
- hemispheres → Consensus;
- Consensus → Interface.

Do not reintroduce uncontrolled cyclic self-feeding solely to make counters move.

## Current validation state
As of this checkpoint:
- server runtime health and independent server cycling have been verified by live Chat diagnostics;
- Android local runtime health and independent local cycling have been verified on device;
- authenticated device/server connection has been verified server-side;
- the remaining target is the **Android Options → Cores rendering of the heartbeat-provided server snapshot in v0.64**.

Treat the v0.64 Cores screen as requiring real-device verification before declaring the telemetry issue closed.

## Development priority after telemetry verification
Once v0.64 proves the correct local/server display, stop iterating on this surface and return to the broader JANUS roadmap. Preserve this bug as a regression test: a future build must not show zero/unknown server cores while an authenticated server diagnostic can see a live server runtime.
