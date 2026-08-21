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
- Root cause of earlier apparent failed Observe fixes: MainActivity.java injected a legacy janusLocalEvidence() renderer after index.html loaded, overwriting the newer Observe renderer. Build workflow now guards against this override.
- v0.43 added a device-local Interface outbox so worthwhile local Interface conclusions can reach Messages without waiting for server sync.
- v0.44 corrected recursive routing/role leakage: no ordinary left<->right recirculation, no Consensus->hemisphere recycling, no Interface->Consensus feedback loop; remote/global feedback is compressed, tagged [feedback-only], and routed through specialist review.
- After v0.44, routine self-assessments/Fano telemetry leaked into Messages. v0.45 tightened both client and server surfacing so routine self-assessment, maintenance, telemetry, generic integration text and near-duplicates stay in Observe.
- Messages are reserved for genuinely new conclusions/findings, questions for the user, warnings, recommendations or other actionable/meaningful follow-ups.
- v0.45 client rendering also filters already-generated low-value telemetry messages so the existing list cleans up without requiring manual dismissal of every stale item.

## Background activity -> Interface/Messages checkpoint
- Verified from Android screenshots that the local 11-core society performs deterministic background processing and that Chat can report the local runtime evidence accurately.
- runtime_messaging.py now consumes local_runtime_evidence from Android chat requests, so Chat cannot claim there was no verified activity when Observe shows recent cycles.
- core_activity_bridge.py persists synced local events to Activity/Memory and can promote substantive Interface conclusions into proactive_message records.
- Android has a complementary local surface path so meaningful Interface conclusions can reach Messages even while server sync is delayed/offline.
- Observe is the detailed process journal; Messages is a sparse, user-relevant outbox. Internal telemetry belongs in Observe unless it produces a meaningful conclusion worth surfacing.

## Forward-only routing / recursive-echo checkpoint
- Live JANUS correctly diagnosed prior role leakage/routing noise: hemispheres were repeatedly being fed previous Consensus/Interface text, causing recursive description of integration rather than continued work on the underlying question.
- Correct ordinary cognition path is strict: specialists -> assigned hemisphere -> Consensus -> Interface.
- Left and right hemispheres do not feed each other directly during ordinary routing. Consensus is the reconciliation point.
- Interface is a surface/output state, not an automatic new thinking topic. Consensus does not feed its result back into either hemisphere.
- Cross-device/global feedback is compressed and tagged [feedback-only], then routed through Context + Counterpoint specialist review rather than injected directly into Consensus/Interface.
- Android forward-routing patch is verified at build time; routing verifier must only flag actual prohibited edges and must not mistake legitimate Safety fan-out for recursion.

## Core-sync 500 checkpoint
- Proven root cause was sqlite3.Row being treated like a dict with .get() in core_sync.py.
- Fixed with safe account-field access and hardened sync stages so one persistence failure returns degraded diagnostics rather than HTTP 500.
- Android already retries sync periodically; no client rebuild was needed for this server-side crash.

## Authentication / account lifecycle checkpoint
- auth.py initializes current auth schema at import; auth_schema_guard.py validates complete required table shapes and preserves incompatible legacy sessions/auth_tokens before recreation.
- SMTP/email delivery is non-fatal to account creation/reset; delivery status is reported separately.
- Added local network-free regression tests for register -> login -> /auth/me, duplicate-account rejection, password reset, session invalidation and required auth table columns.
- Added authenticated logout lifecycle endpoints: /auth/logout revokes the current bearer session; /auth/logout-all revokes all sessions for the account. Regression coverage verifies session invalidation.
- Added GitHub Actions auth regression workflow so auth/security changes are automatically tested.
- secure_desktop.py binds private desktop routes to the authenticated account username and ignores client attempts to select another profile. Added regression coverage for cross-user profile spoofing and invalid-session rejection.
- Google-only account lifecycle edge fixed for new accounts: password_hash is explicitly marked google_only rather than using an unreachable random PBKDF2 password. Password login rejects the marker; account deletion can therefore distinguish Google-only accounts correctly. Existing password accounts linked to Google keep their real password hash.
- Non-Google account creation/login still requires end-to-end verification against the live Render persistent database from a real client.

## Windows / PC checkpoint
- The previously packaged Windows v0.21 client used free-form profile selection and sent no bearer token, so it was structurally incompatible with secure_desktop's authenticated private routes.
- Added client/janus_client_v022.py as an authenticated compatibility layer over the feature-complete v0.21/v0.20 UI chain.
- Windows v0.22 adds username/email + password sign-in, Create Account, persisted session token restore, bearer-authenticated private Chat/Messages/Observe/Cores/Memory/Activity/Settings requests, and Sign Out.
- The authenticated account username, not a typed profile, becomes the active JANUS profile.
- build-windows.yml now syntax-checks the v0.20/v0.21/v0.22 chain before PyInstaller and builds JANUS.exe from v0.22. Artifact name is JANUS-Windows-v0.22.
- Windows v0.22 still needs real Windows launch/use testing by the user after CI produces the executable.

## Apple / iOS checkpoint
- Existing iOS scaffold was also using arbitrary profile names and unauthenticated private requests.
- APIClient.swift now persists a JANUS bearer token, supports username/email + password login, account registration, /auth/me session restore and /auth/logout, and attaches Authorization headers to private JANUS requests.
- Models.swift contains Account/AuthResponse/MeResponse models for the auth lifecycle.
- ContentView.swift now gates the app on a real JANUS account, provides Sign in/Create account UI, restores saved sessions, uses the authenticated account username as the profile, and exposes Sign out.
- iOS signing/certificates/Apple Developer account are not required for this source work. Simulator CI should be used to catch Swift compile errors before device signing work.
- Sign in with Apple and native Apple-device background behaviour remain later tasks requiring platform/account input.

## Android build / APK delivery checkpoint
- GitHub Actions builds the debug APK and force-publishes orphan branch apk-download with downloads/JANUS-Android-v<version>.apk and oauth-build-info.txt.
- v0.44 publication was delayed by invalid workflow YAML from embedding a large JavaScript block directly in workflow YAML. Patch logic was moved into dedicated Python scripts and workflow simplified.
- A further build blocker came from an over-broad routing-verifier assertion that falsely matched legitimate Safety fan-out. The verifier was corrected to check only real forbidden edges.
- Before giving any APK link, verify the actual apk-download branch contains the requested version. Never infer publication from a version bump or commit alone.
- Direct-download form: https://raw.githubusercontent.com/Vardath/JANUS/apk-download/downloads/JANUS-Android-v<version>.apk

## Current Android OAuth identity
Package: com.vardath.janus
Google web client ID currently configured in source fallback: 236215282074-7s6uj0tdeen1r3ptcpd2nlmkam97j0l3.apps.googleusercontent.com
Stable debug signing key is cached by the GitHub Actions workflow; oauth-build-info.txt records the exact built certificate fingerprints and generated client ID for each APK.

## Near-term product backlog
- Live-verify non-Google registration/login on deployed Render and fix any remaining persistent-schema/runtime issue.
- Configure/test email verification and password-reset SMTP flow.
- Re-test Google login end-to-end and account linking/merging.
- Verify Windows v0.22 CI artifact and then test executable on a real Windows PC.
- Compile/test iOS simulator build; later add Sign in with Apple, signing, TestFlight/device testing and background-behaviour adaptation.
- Cross-device identity/state synchronization, offline recovery, security/privacy audit, deployment reliability, cost controls and multi-day soak testing.

## Working practice
- Keep this file current after material architecture, build, authentication, UI, persistence or deployment changes.
- Verify claims against repository/build outputs rather than inferring success from a version bump or commit alone.
- Trace UI behavior end-to-end across client asset, platform code injection, client request payload, secure server wrapper, active server route implementation, persistence layer, and UI reader before declaring a fix complete.
- When supplying an APK, give the verified direct-download target rather than merely a GitHub directory or expected filename.
