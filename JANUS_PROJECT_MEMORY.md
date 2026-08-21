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

## Android checkpoint: v0.44 published; v0.45 message-filter build
- Android v0.44 is published and verified on apk-download. It contains the forward-only local-core routing correction.
- Observe UI has readable externalizable process-journal cards, expandable Technical details, incremental DOM updates, scroll-position preservation and a New thoughts indicator.
- Root cause of earlier apparent failed Observe fixes: MainActivity.java injected a legacy janusLocalEvidence() renderer after index.html loaded, overwriting the newer Observe renderer. Build workflow now guards against this override.
- v0.43 added a device-local Interface outbox so worthwhile local Interface conclusions can reach Messages without waiting for server sync.
- v0.44 corrected recursive routing/role leakage: no ordinary left<->right recirculation, no Consensus->hemisphere recycling, no Interface->Consensus feedback loop; remote/global feedback is compressed, tagged [feedback-only], and routed through specialist review.
- After v0.44, a Messages regression was observed: routine self-assessments, Fano-direction telemetry, repeated Interface reformulations and near-duplicates were being surfaced as user-facing Observations. This was a surfacing/filtering problem, not a core-routing failure.
- v0.45 tightens the Interface->Messages gate on both client and server. Routine self-assessment, maintenance, telemetry, generic integration text and near-duplicates stay in Observe. Messages are reserved for genuinely new conclusions/findings, questions for the user, warnings, recommendations or other actionable/meaningful follow-ups.
- v0.45 client rendering also filters already-generated low-value telemetry messages so the existing list cleans up without requiring manual dismissal of every stale item.
- Do not call v0.45 ready until apk-download actually publishes JANUS-Android-v0.45.apk.

## Background activity -> Interface/Messages checkpoint
- Verified from Android screenshots that the local 11-core society performs deterministic background processing and that Chat can report the local runtime evidence accurately.
- runtime_messaging.py now consumes local_runtime_evidence from Android chat requests, so Chat cannot claim there was no verified activity when Observe shows recent cycles.
- core_activity_bridge.py persists synced local events to Activity/Memory and can promote substantive Interface conclusions into proactive_message records.
- Android has a complementary local surface path so meaningful Interface conclusions can reach Messages even while server sync is delayed/offline.
- Important rule after v0.45: Observe is the detailed process journal; Messages is a sparse, user-relevant outbox. Internal telemetry belongs in Observe unless it produces a meaningful conclusion worth surfacing.

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

## Account creation HTTP 500 checkpoint
- Android still returned HTTP 500 from POST /auth/register after core-sync repair.
- auth.py defined init_auth_db() but did not call it; fixed by running auth schema initialization at import.
- SMTP/email verification delivery is non-fatal: email_delivery=false rather than account-creation HTTP 500.
- Added auth_schema_guard.py to validate complete required auth table shapes, preserve incompatible legacy tables, and recreate current sessions/auth_tokens schemas safely.
- /diagnostics/auth-config reports live deployed commit marker, route presence, guard actions and non-secret auth table columns.
- Account creation/login without Google remains one of the main unfinished product tasks and must be re-tested end-to-end on the deployed Render service.

## Android build / APK delivery checkpoint
- GitHub Actions builds the debug APK and force-publishes orphan branch apk-download with downloads/JANUS-Android-v<version>.apk and oauth-build-info.txt.
- v0.44 publication was delayed by an invalid build-android.yml YAML file caused by embedding a large JavaScript block directly in workflow YAML. The fix moved patch logic into dedicated Python scripts and simplified the workflow.
- A further build blocker came from an over-broad routing-verifier assertion that falsely matched legitimate Safety fan-out. The verifier was corrected to check only real forbidden edges.
- Before giving any APK link, verify the actual apk-download branch contains the requested version. Never infer publication from a version bump or commit alone.
- Direct-download form: https://raw.githubusercontent.com/Vardath/JANUS/apk-download/downloads/JANUS-Android-v<version>.apk

## Current Android OAuth identity
Package: com.vardath.janus
Google web client ID currently configured in source fallback: 236215282074-7s6uj0tdeen1r3ptcpd2nlmkam97j0l3.apps.googleusercontent.com
Stable debug signing key is cached by the GitHub Actions workflow; oauth-build-info.txt records the exact built certificate fingerprints and generated client ID for each APK.

## Near-term product backlog
- Finish non-Google account creation and login, including registration, login, session persistence, password reset, email verification and useful error handling.
- Re-test Google login end-to-end and account linking/merging.
- Windows/PC client parity, packaging and long-run testing.
- Apple/iOS/macOS development, signing and background-behaviour adaptation.
- Cross-device identity/state synchronization, offline recovery, security/privacy audit, deployment reliability, cost controls and multi-day soak testing.

## Working practice
- Keep this file current after material architecture, build, authentication, UI, persistence or deployment changes.
- Verify claims against repository/build outputs rather than inferring success from a version bump or commit alone.
- Trace UI behavior end-to-end across client asset, MainActivity JavaScript injection, client request payload, secure server wrapper, active server route implementation, persistence layer, and UI reader before declaring a fix complete.
- When supplying an APK, give the verified direct-download target rather than merely a GitHub directory or expected filename.