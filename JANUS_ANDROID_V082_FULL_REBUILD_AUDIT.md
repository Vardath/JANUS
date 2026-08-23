# JANUS Android v0.82 full-rebuild audit

Date: 2026-08-24
Status: authoritative Android client implementation; CI/device acceptance still required.

## Rebuild rule

The Android product is rebuilt as a native client under `android/`. The old WebView/HTML UI and build-time Android patch/composer chain are not part of the authoritative build. The server/global JANUS core remains authoritative for accounts, continuity, memory, research, files, image generation, maintenance and protected state.

The first launch of this rebuilt line clears the previous Android client's app-private JANUS preferences once. It does not import old client tokens, queues, local-core counters, UI state or cached preferences. Server-owned account state is recovered only through successful authentication.

## Architecture invariants audited

- 11 cores total: Evidence, Logic, Counterpoint, Context, Memory, Safety, Novelty -> Left Hemisphere / Right Hemisphere -> Consensus -> Interface.
- Local routing is forward-only. No left/right recirculation, Consensus-to-hemisphere recycling or Interface-to-Consensus feedback.
- Remote/global material is feedback-only and re-enters through specialists.
- Deterministic local cycles use zero model/API calls; paid background language work remains separately bounded/disabled by default.
- Protected server identity/core state is not overwritten by client preferences or whole-state sync.
- Account/session boundaries remain server-authenticated; client-supplied username/profile values are not authorization.

## Product surface audited

### Authentication and account lifecycle

Native sign in, create account, Google identity bridge, session restore, forgot/reset password, email verification/resend, sign out, sign out all devices and permanent account deletion are present. Password login uses the current server `identifier` contract. Google still requires the exact Android package/signing certificate to be registered in the same Google Cloud project as the JANUS Web client ID.

### Chat

Native Chat provides a responsive composer, one visible user turn per send, stable `client_message_id`, bounded retry/offline queue, attachment IDs, server-grounded replies, source/provenance display, generated-image display and per-response reporting. Foreground Chat does not depend on optional background budgets.

### Messages

JANUS-originated useful prompts/conclusions are loaded separately from Observe telemetry. Background notification checks and offline reply recovery remain bounded.

### Observe and core visibility

Observe renders externalizable local/server activity without exposing private chain-of-thought. Runtime Cores exposes the 7 -> 2 -> 1 -> 1 society and per-core state/Fano telemetry. Refresh is user-controlled/stable rather than a rapid UI reset loop.

### Options and product screens

The native Options surface links to Runtime Cores, Memory, Activity, System Status, Compatibility, Research Workspace, Artifacts, Background Research, Maintenance Review, Settings and Account. These are native screens within the one launcher flow.

### Files and artifacts

Native file picker supports up to four account-bound uploads per Chat turn. Generated artifacts support continuity report, research digest and working note creation plus authenticated open/download/export/share through Android document/share flows and FileProvider.

### Research and web/media

Research Workspace uses the server research ledger and preserves established/provisional/negative/open/proposed-test distinctions. Foreground public URL/web/YouTube/transcript retrieval remains a server capability and returned evidence retains provenance. Background Research displays externalizable sources, usefulness/suppression decisions and external-compute estimates.

### Images

Explicit user image requests and rare explanatory images use the bounded server image service at medium quality. Returned generated images are shown in Chat. Autonomous multi-core background image rendering remains disabled/economically gated.

### Maintenance

Owner-only maintenance review supports approve-for-manual-work, defer and reject. Approval never authorizes JANUS to edit code, install dependencies, change models/APIs/configuration or deploy autonomously.

### Settings

System/light/dark appearance, accent choices, Observe telemetry and device-local background/sleep cadence are client settings. They do not modify protected JANUS cognition state.

### Reliability and compatibility

The client exposes human-readable runtime health and `/protocol/capabilities`. Network work runs off the UI thread. Optional capability failures must degrade locally rather than freeze navigation. The offline queue is bounded and retry-safe.

## CI release gate

The authoritative Android workflow must:

1. Reject WebView/HTML UI reintroduction and build-time Android patch/composer dependencies.
2. Verify the native product screen/function markers and server route contracts.
3. Verify forward-only local 11-core routing and feedback-only remote sync.
4. Compile Java explicitly before assembling the APK.
5. Assemble the real `android/` application with the stable signing key.
6. Publish only the current-head APK and build identity.

A green static/build gate is necessary but not sufficient for release acceptance.

## Real-device acceptance gate

Before calling the rebuild known-good, install the current-head APK and verify: fresh login screen; password sign-in; session restore; Google sign-in after OAuth registration; Chat round trip; generated image request; URL/web/YouTube research; offline queue/recovery; Messages; stable Observe; all 11 core views; text/PDF/image attachments; artifact create/open/export/share; Research Workspace; Background Research; Maintenance owner/non-owner behavior; themes/background preferences; account sign-out/delete behavior; and process restart/relaunch.

Historical red runs from pre-v0.82 clients are not evidence about the current rebuilt client. Release decisions must use the workflow run whose commit matches current `main`.
