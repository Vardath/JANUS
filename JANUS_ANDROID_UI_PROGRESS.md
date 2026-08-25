# JANUS Android UI Improvement Progress

Updated: 2026-08-25

## Authoritative baseline
- Native `android/` client only; no WebView/generated HTML/patch-composer product path.
- Production server: `server_v2/`.
- Runtime topology: 7 specialists -> 2 hemispheres -> Front/stream -> Interface.
- Preserve forward-only outward routing, feedback-only federation, stable Observe/Stream snapshots, zero-API deterministic local cycles, authenticated account ownership, and owner-gated maintenance.
- JANUS may diagnose/report its own externalizable failures, but may not approve maintenance, edit source, install packages, change model/API configuration, or deploy itself.

## Verified published passes
- v0.83-v0.96: native safe areas, Chat/product polish, Cores/Observe architecture, Memory/Research/Account improvements, Reply-in-Chat, structured sources/images, accessibility and shared Chat-controller foundations.
- v0.97: queued delivery moved onto the shared Chat controller/API stack; generated-image metadata restored after restart.
- v0.98: foreground `/desktop/chat` API posts cross the shared controller boundary; structured history v2 introduced alongside legacy history.
- v0.99: structured history v2 became an independent bounded store with one-way legacy migration.
- v1.00: structured Chat v2 became the visible surface authority.
- v1.01: foreground Chat switched directly to `JanusChatController`; live `Sources:` appendix removed; structured v2 history became the normal read/write path.
- v1.02: queued/offline replay retained structured sources/generated-image metadata; obsolete v1 bridge classes retired.
- v1.03: Messages and read-only Observe gained dedicated native screen owners.
- v1.04: client-side Copy/Share duplication, full-tree typing lag and stray Observe-guide regression fixed with idempotent/debounced decorators; published APK verified.
- v1.05: Android system Back navigation adapter + hidden device background-activity bridge introduced; published APK verified, but Back still failed on the real Samsung device because predictive-back callback enablement was not explicit.
- v1.06: natural background-thought questions now surface real persisted local processing; seven persistent Fano directions became active computational attention orientations; published APK verified and Chat behavior validated on-device.
- v1.07: theme-aware system chrome, explicit predictive-Back enablement and hardware-safe Runtime Cores renderer; published APK verified pending wider real-device validation.
- v1.08: governed self-diagnosis, retained server-side Chat history from v1.08 onward, client crash replay, owner-controlled Supervisor handoff and maintenance decision return path.
- v1.09 stability pass: detail-screen crashes persisted after surface reset/navigation changes. Investigation identified multiple independent global-layout polish/injection layers as a plausible shared source. A stability-first build disabled competing cosmetic/runtime view-tree injection while preserving native screens, system chrome, Back handling, crash diagnostics and governed maintenance handoff. Authoritative Java compile and APK assembly passed and the build was published.

## Real-device findings after v1.09

### Detail-screen stability
The exact original shared crash mechanism is not yet proven. v1.09 deliberately removes fragile decoration layers so future diagnosis can distinguish native screen faults from presentation-stack faults. If a detail screen still closes, use the retained `JanusClientDiagnostics` exception report and expose it in-app before making another speculative structural fix.

### Theme / colour bug
The current JANUS colour/theme controls are affecting the **Android phone/system theme or system chrome rather than JANUS app-only colours**. This is incorrect. Theme settings must be scoped to JANUS-owned views/resources only. They must not change the user's device theme, global Android appearance, or other apps.

### Navigation usability
The current menu set is usable enough to continue. This gives a stable starting point for a deliberate UI rebuild instead of continuing incremental cosmetic patches.

## v1.08 — governed self-diagnosis and ChatGPT Supervisor maintenance loop
### Requested behavior
JANUS should notice when Chat encounters a capability it cannot perform or when the client detects a failure, maintain a request list, surface that list to the owner in Messages, prepare a complete Supervisor handoff, and later show the owner which requests ChatGPT approved/disapproved and what was actually implemented.

### Governance boundary
JANUS diagnoses and requests; it does not authorize or execute maintenance. `automatic_code_changes=false`, `automatic_deploy=false`, and protocol invariants explicitly state that JANUS cannot self-modify, self-approve maintenance or self-deploy. There is deliberately no silent injection into an arbitrary ChatGPT conversation.

### Server implementation
- New `server_v2/diagnostics.py` owns a persistent `v2_capability_requests` ledger and a `v2_chat_history_full` ledger.
- Every authoritative `/desktop/chat` turn records the exact visible user message and Interface reply from v1.08 onward. Hidden device-background context is kept separate using Android's `user_visible_message` field.
- Returned/interface text is scanned only for externalizable failure signals such as unavailable/unsupported/not-configured/model-call-failed/budget-reached conditions; explicit future tool/core `capability_requests` metadata is also supported.
- Requests are deduplicated by fingerprint, accumulate occurrence counts, and reopen if a supposedly implemented failure reappears.
- A new request creates an unread JANUS Message describing the capability, severity and reason it has been queued for Supervisor review.
- `/maintenance/requests` exposes the ledger to the authenticated account.
- `/maintenance/supervisor-handoff` is owner-only and generates one complete packet containing the request ledger, all server-retained Chat turns, and an explicit command to ChatGPT Supervisor to review the private `Vardath/JANUS` repo, audit each request, approve/disapprove independently, implement approved items only, run regression/build audits, update repo records and write decisions to the decision ledger.
- `/maintenance/diagnostics/report` accepts authenticated externalizable client/tool failure reports but has no maintenance authority.

### Android implementation
- `JanusClientDiagnostics` installs a bounded uncaught-exception capture. An Android crash is stored locally as exception type/message + short stack trace and submitted to the governed diagnostic endpoint on the next authenticated resume. If submission fails it stays queued; reporting failure cannot recursively crash-report itself.
- `JanusApiClient` always sends `user_visible_message` before optional hidden device-thought augmentation so Supervisor history never misattributes hidden context to the user.
- `JanusMaintenanceSupervisorPolish` adds owner-controlled `Copy handoff` and `Share to ChatGPT` actions to Maintenance Review. Nothing is transmitted automatically.
- Existing Messages UI naturally receives `capability_request` and later `supervisor_decision` messages through the established server message channel.

### ChatGPT Supervisor decision return path
- `server_v2/supervisor_decisions.json` is repo-owned and explicitly not JANUS-writable.
- While performing a requested maintenance pass, ChatGPT Supervisor records each request's `approved`, `disapproved` or `deferred` decision, reason, implementation state and implemented version in that file.
- On the next deployed server startup, `diagnostics.apply_supervisor_decisions()` applies previously unseen decisions to the request ledger and creates an unread `supervisor_decision` Message for the owner.
- This means the owner can see both what JANUS requested and what ChatGPT rejected/deferred/implemented, including requests that did not make it into a release.

### History limitation
The server cannot reconstruct Chat text that was never stored before v1.08. The handoff is complete for server-retained history from v1.08 deployment onward; older local Android history remains local unless separately supplied/exported. The handoff packet says this explicitly instead of claiming false completeness.

## Next Android UI session

The next pass is a rebuild/simplification pass, not another layer of runtime polish.

1. Fix the app-theme scope bug first: JANUS colour settings must style JANUS only.
2. Redesign for cleaner reading, simpler hierarchy and easier navigation.
3. Reduce dependence on native Android button/control styling and fragile assumptions about system control geometry.
4. Keep JANUS controls and Android/system controls visually and spatially separate so both remain safe to use.
5. Nothing important may sit behind, overlap, or be obscured by system navigation/buttons, predictive-back affordances, status/navigation bars, keyboards, accessibility overlays, or JANUS's own persistent controls.
6. Prefer explicit screen-owned layouts/components over global view-tree scanning, rewriting or injection.
7. Preserve safe-area handling, predictive/system Back behavior, accessibility, existing functional menus, Chat history, diagnostics, Messages, Stream/Observe and maintenance governance.
8. Real-device test Cores, Memory, Settings, Stream, Messages, Observe and Options after each major layout milestone.
9. If crashes remain, surface the exact stored crash report in-app with copy/share and fix from the stack trace.

Do not restore the old global-layout cosmetic stack merely to regain visual polish. Clean ownership and deterministic rendering are the new UI baseline.
