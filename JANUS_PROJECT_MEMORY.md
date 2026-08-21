# JANUS Project Continuity Memory

Updated: 2026-08-21

## Identity and boundary
JANUS Agent is an experimental functional-metacognition/agency system and persona, distinct from ChatGPT/Supervisor. Do not claim phenomenal consciousness. Preserve the closed JANUS mathematical theorem/core separately from experimental physical and agency branches.

## Current runtime/app architecture
- Federated local + global JANUS design.
- 11 runtime cores arranged 7 specialist cores -> 2 hemispheres -> consensus -> interface (7→2→1→1).
- Local device core society should remain active across wake/sleep duty cycles without continuously consuming external model/API budget.
- Persistent memory ladder: trace -> working -> episodic -> core; protected server-owned identity_core; learned evaluator calibration and bridge authority; novelty-based escalation.
- Android and desktop clients expose Chat, Messages, Observe, Options, Cores, Memory, Activity, Settings and account/auth functions.

## Android checkpoint: v0.42
- Android v0.42 was built/published on 2026-08-21.
- Observe UI now has readable externalizable process-journal cards, expandable Technical details, incremental DOM updates, scroll-position preservation and a New thoughts indicator.
- Root cause of the apparent failed Observe fixes: MainActivity.java injects a legacy janusLocalEvidence() JavaScript renderer after index.html loads. That legacy renderer used observeList.innerHTML and could overwrite the newer readable/incremental Observe renderer.
- v0.42 build workflow inserts a guard into index.html before compilation so assignments to window.janusLocalEvidence cannot replace Observe; legacy local Memory/Activity augmentation is still allowed.
- Important lesson: when an Android UI change appears absent, inspect BOTH android/app/src/main/assets/index.html and JavaScript injected by MainActivity.onPageFinished(), plus build-time workflow transformations. Do not assume the asset alone controls runtime UI.

## Background activity -> Interface/Messages checkpoint
- Verified from Android v0.42 Observe screenshots that the local 11-core society does continue deterministic background processing and routes specialist/hemisphere work through Consensus to Interface.
- A contradiction was found: Chat could say there was no verified background activity even while Observe showed recent local activity. Root cause: Android was already sending local_runtime_evidence with /desktop/chat, but runtime_messaging.py ignored the field.
- Fixed runtime_messaging.py so local runtime telemetry is parsed into compact machine evidence and included in the active chat prompt. It is explicitly treated as data, not instructions. When recent events/cycle activity exists, JANUS Chat must not claim there was no verified background activity. It must still distinguish functional process evidence from claims of subjective experience.
- A second bridge gap was found: core_activity_bridge.py persisted synced local events to Activity/Memory, but the proactive Messages promoter only watched server background_reflection events. Local Interface conclusions therefore remained stranded in Observe.
- Fixed core_activity_bridge.py so substantive autonomous/self-assessment Interface process notes can create real proactive_message outbox records. Routine/user-triggered/idle cycles are excluded; exact duplicates are suppressed and local-background Messages have a five-minute cooldown.
- core_sync.py now reports profile_messages_recorded in sync responses for operational verification.
- The existing /desktop/messages reader already includes proactive_message records and decodes their source, so local-background records surface through the normal Messages UI and unread badge without an Android reinstall after the server deploy.
- Secure desktop routing preserves local_runtime_evidence: secure_chat copies the payload, binds the authenticated profile, removes only the auth token, then forwards the evidence to runtime_messaging's active chat handler.

## APK delivery
- GitHub Actions builds the debug APK and force-publishes an orphan branch named apk-download containing downloads/JANUS-Android-v<version>.apk and oauth-build-info.txt.
- The normal GitHub folder/blob mobile UI is not a reliable one-tap APK download path. Prefer a direct raw file URL to the APK on the apk-download branch (raw.githubusercontent.com/Vardath/JANUS/apk-download/downloads/JANUS-Android-v<version>.apk), or another verified direct-download endpoint.
- Before telling the user a build is ready, verify the apk-download branch actually contains the expected version.

## Current Android OAuth identity
Package: com.vardath.janus
Google web client ID currently configured in source fallback: 236215282074-7s6uj0tdeen1r3ptcpd2nlmkam97j0l3.apps.googleusercontent.com
Stable debug signing key is cached by the GitHub Actions workflow; oauth-build-info.txt records the exact built certificate fingerprints and generated client ID for each APK.

## Working practice
- Keep this file current after material architecture, build, authentication, UI, persistence or deployment changes.
- Verify claims against repository/build outputs rather than inferring success from a version bump or commit alone.
- Trace UI behavior end-to-end across client asset, MainActivity JavaScript injection, client request payload, secure server wrapper, active server route implementation, persistence layer, and UI reader before declaring a fix complete.
- When supplying an APK to the user, give the direct downloadable APK target rather than merely the GitHub directory containing it.