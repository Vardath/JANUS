# JANUS Project Continuity Memory

Updated: 2026-08-21

## Identity and boundary
JANUS Agent is an experimental functional-metacognition/agency system and persona, distinct from ChatGPT/Supervisor. Do not claim phenomenal consciousness. Preserve the closed JANUS mathematical theorem/core separately from experimental physical and agency branches.

## Current runtime/app architecture
- Federated local + global JANUS design.
- 11 runtime cores arranged 7 specialist cores -> 2 hemispheres -> consensus -> interface (7→2→1→1).
- Local device core society remains active across wake/sleep duty cycles without continuously consuming external model/API budget.
- Persistent memory ladder: trace -> working -> episodic -> core; protected server-owned identity_core; learned evaluator calibration and bridge authority; novelty-based escalation.
- Android and desktop clients expose Chat, Messages, Observe, Options, Cores, Memory, Activity, Settings and account/auth functions.
- Current ordinary cognition routing is forward-only: evidence/logic/counterpoint -> left hemisphere; context/memory/novelty -> right hemisphere; both hemispheres -> Consensus; Consensus -> Interface. Safety may advise left/right/Consensus. Interface is output/surface state, not automatic re-entry.

## Android checkpoint: v0.45 published
- Android v0.45 is published and verified on apk-download. It contains the forward-only routing correction plus tightened Messages filtering.
- Observe UI has readable externalizable process-journal cards, expandable Technical details, incremental DOM updates, scroll-position preservation and a New thoughts indicator.
- v0.43 added a device-local Interface outbox so worthwhile local Interface conclusions can reach Messages without waiting for server sync.
- v0.44 corrected recursive routing/role leakage: no ordinary left<->right recirculation, no Consensus->hemisphere recycling, no Interface->Consensus feedback loop; remote/global feedback is compressed, tagged [feedback-only], and routed through specialist review.
- v0.45 keeps routine self-assessment, maintenance, Fano telemetry and generic integration text in Observe; Messages are reserved for genuinely useful conclusions/questions/warnings/recommendations.

## Forward-only routing / cross-device checkpoint
- Correct ordinary cognition path is strict: specialists -> assigned hemisphere -> Consensus -> Interface.
- routing_policy.py overrides both _route_output and accept_remote_summary. Synchronized client Consensus/Interface state is compressed, tagged [feedback-only], and routed through Context + Counterpoint rather than injected directly into Consensus/Interface.
- tests/test_routing_policy.py plus GitHub Actions routing CI fail if left/right cross-feed, Consensus->hemisphere feedback, Interface->Consensus feedback, or direct remote-summary injection returns.
- Remembered remote-device summaries are now bounded (default 100). When the cap is exceeded, the oldest summaries are removed both from memory and janus_core_remote_summary so abandoned/reinstalled device IDs cannot grow indefinitely.

## Offline chat / receipt security checkpoint
- Android JanusOfflineQueue gives each queued chat turn a client_message_id, persists undelivered turns locally, retries later and stores deferred replies.
- Server janus_chat_receipts makes retries idempotent so a response lost after server acceptance does not duplicate the user turn.
- chat_receipt_security.py now binds every cached receipt to the authenticated profile. A colliding client_message_id from another account cannot read, replay or overwrite the original account's cached result. Regression coverage was added.
- Temporary chat receipts are retained for 7 days by default and then pruned by retention.py.

## Runtime retention / persistence checkpoint
- User conversation/memory content remains continuity data and is not globally aged out by the temporary-data cleaner.
- retention.py now additionally removes janus_chat_receipts older than JANUS_CHAT_RECEIPT_RETENTION_DAYS (default 7), repetitive core_runtime_snapshot events older than JANUS_RUNTIME_SNAPSHOT_RETENTION_DAYS (default 30), and matching snapshot ingest-claim rows.
- Existing cleanup still removes expired sessions, expired/old-used auth tokens and stale pending deletion requests.
- This keeps the 1 GB Render disk from filling with retry receipts and cycle-counter telemetry during multi-device/soak testing.

## Render/runtime reliability checkpoint
- Render now builds directly with `pip install -r requirements.txt` and launches `uvicorn bootstrap:app`; obsolete server.py base64/gzip reconstruction was removed.
- Duplicate inline Google client configuration was removed from the start command; Render env vars are the single source of truth.
- bootstrap.py exposes /diagnostics/runtime-health with deployed commit, SQLite quick_check/writability, auth-schema validity, core persistence, core phase/count, remote-client count, background API usage and receipt-guard status. Degraded bootstrap routes remain available if the full app fails to import.
- Live deployment of the newest diagnostics still requires external verification after Render deploy propagation; do not infer deployment success solely from commit state.

## API/cost-control checkpoint
- autonomous_hive.py already has per-profile paid-background daily call/token budgets and escalation thresholds.
- Production Render now sets JANUS_PAID_BACKGROUND_REFLECTION=0 by default. Deterministic local/server hive/core cycles remain active and zero-API; ordinary user-triggered Chat still uses JANUS_MODEL.
- Conservative dormant caps are configured for any later deliberate re-enable: JANUS_BACKGROUND_DAILY_CALL_CAP=12 and JANUS_BACKGROUND_DAILY_TOKEN_CAP=20000 per profile/day.
- Do not re-enable paid background reflection broadly until pricing/product policy and scale limits are intentionally decided.

## Authentication / account lifecycle checkpoint
- auth.py initializes current auth schema at import; auth_schema_guard.py validates complete required table shapes and preserves incompatible legacy sessions/auth_tokens before recreation.
- SMTP/email delivery is non-fatal to account creation/reset; delivery status is reported separately.
- Regression tests cover register -> login -> /auth/me, duplicate-account rejection, password reset, session invalidation, logout, required auth columns and cross-user profile spoofing.
- Google-only account lifecycle marker is explicit; password login rejects Google-only accounts while account deletion can distinguish them correctly.
- Non-Google registration/login still requires end-to-end verification against the deployed Render persistent database from a real client.

## Windows / PC checkpoint
- Windows v0.22 is an authenticated compatibility layer over the feature-complete v0.21/v0.20 UI chain.
- Adds username/email + password sign-in, Create Account, bearer-authenticated private screens, session restore and Sign Out.
- Session tokens are persisted with Windows DPAPI bound to the current Windows user; passwords are never stored.
- build-windows.yml syntax-checks the client chain before PyInstaller and builds JANUS.exe from v0.22. Real Windows launch/use testing still requires the user.

## Apple / iOS checkpoint
- iOS now uses real JANUS accounts rather than arbitrary profile names.
- APIClient supports login/register/me/logout and authenticated private requests; tokens are stored in Keychain, not UserDefaults.
- ContentView gates the app on a valid account and exposes Sign in/Create account/Sign out.
- Build JANUS iOS Simulator workflow exists for unsigned simulator compilation; real Apple signing/TestFlight/device testing still requires Apple-account/device input.

## Near-term product backlog
- Live-verify non-Google registration/login on deployed Render and fix any remaining persistent-schema/runtime issue.
- Configure/test email verification and password-reset SMTP flow.
- Re-test Google login end-to-end and account linking/merging.
- Verify Windows v0.22 CI artifact and test executable on a real Windows PC.
- Verify iOS simulator CI result; later add Sign in with Apple, signing, TestFlight/device testing and Apple background-behaviour adaptation.
- Continue privacy/security audit, multi-day soak testing and decide eventual user-triggered/paid-background quota policy before scaling.

## Working practice
- Keep this file current after material architecture, build, authentication, UI, persistence or deployment changes.
- Verify claims against repository/build outputs rather than inferring success from a version bump or commit alone.
- Trace UI behavior end-to-end across client asset, platform code injection, client request payload, secure server wrapper, active server route implementation, persistence layer, and UI reader before declaring a fix complete.
- Before giving any APK link, verify the actual apk-download branch contains the requested version.
