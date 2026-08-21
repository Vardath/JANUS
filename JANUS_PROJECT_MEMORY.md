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
- When supplying an APK to the user, give the direct downloadable APK target rather than merely the GitHub directory containing it.
