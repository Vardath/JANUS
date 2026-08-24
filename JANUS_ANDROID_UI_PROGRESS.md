# JANUS Android UI Improvement Progress

Updated: 2026-08-24

## Authoritative baseline
- Native `android/` client only; no WebView/generated HTML/patch-composer product path.
- Production server: `server_v2/`.
- Runtime topology: 7 specialists -> 2 hemispheres -> Consensus -> Interface.
- Preserve forward-only routing, feedback-only federation, stable Observe snapshots, zero-API deterministic local cycles, authenticated account ownership, and owner-gated maintenance.
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
- `JanusApiClient` now always sends `user_visible_message` before optional hidden device-thought augmentation so Supervisor history never misattributes hidden context to the user.
- `JanusMaintenanceSupervisorPolish` adds owner-controlled `Copy handoff` and `Share to ChatGPT` actions to Maintenance Review. Nothing is transmitted automatically.
- Existing Messages UI naturally receives `capability_request` and later `supervisor_decision` messages through the established server message channel.

### ChatGPT Supervisor decision return path
- `server_v2/supervisor_decisions.json` is repo-owned and explicitly not JANUS-writable.
- While performing a requested maintenance pass, ChatGPT Supervisor records each request's `approved`, `disapproved` or `deferred` decision, reason, implementation state and implemented version in that file.
- On the next deployed server startup, `diagnostics.apply_supervisor_decisions()` applies previously unseen decisions to the request ledger and creates an unread `supervisor_decision` Message for the owner.
- This means the owner can see both what JANUS requested and what ChatGPT rejected/deferred/implemented, including requests that did not make it into a release.

### History limitation
The server cannot reconstruct Chat text that was never stored before v1.08. The handoff is complete for server-retained history from v1.08 deployment onward; older local Android history remains local unless separately supplied/exported. The handoff packet says this explicitly instead of claiming false completeness.

## v1.08 release rule
Do not merge until:
1. self-diagnosis/decision-ledger/server Python syntax and governance gate passes;
2. Android visible-message preservation, crash replay and Supervisor copy/share gate passes;
3. v1.07 system chrome/Back/CoreMap regression remains green;
4. v1.06 thought/Fano regression remains green;
5. v1.04 Chat performance regression remains green;
6. maintenance/auth/protocol/UI hardening checks remain green;
7. authoritative Java compilation and APK assembly succeed;
8. after merge, verify `apk-download` records `Publish JANUS Android native v1.08`.

## Required v1.08 validation
- Ask JANUS for something that truly cannot be completed/configured and confirm a capability-request Message appears without JANUS claiming it fixed itself.
- Open Maintenance Review and confirm Copy/Share Supervisor handoff is present and explicitly owner-controlled.
- Confirm the packet contains the request list, repo-review command and all chat retained since v1.08.
- After a future ChatGPT maintenance review/deployment, confirm Messages shows APPROVED/DISAPPROVED/DEFERRED outcomes plus implementation state/version.
- Reconfirm v1.07 Back/theme/Cores behavior, v1.06 between-message thought reporting and v1.04 typing responsiveness.
