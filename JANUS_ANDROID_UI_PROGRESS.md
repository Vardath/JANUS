# JANUS Android UI Improvement Progress

Updated: 2026-08-24

## Authoritative baseline
- Native `android/` client only; no WebView/generated HTML/patch-composer product path.
- Production server: `server_v2/`.
- Runtime topology: 7 specialists -> 2 hemispheres -> Consensus -> Interface.
- Preserve forward-only routing, feedback-only federation, stable Observe snapshots, zero-API deterministic local cycles, authenticated account ownership, and owner-gated maintenance.

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

## v1.07 — system chrome, Back reliability and Runtime Cores stability
### Device-observed failures after v1.06
1. The status-bar and navigation-bar inset areas remained white even when JANUS used the dark theme.
2. Android system Back still exited the Activity instead of following JANUS' internal page/subpage hierarchy.
3. Opening `Options -> Cores` showed a loading/working state and Android reported an app bug before JANUS closed. The high-risk component on that surface was the dynamically injected custom architecture canvas, which forced software rendering and used shadow/path drawing.

### v1.07 implementation
- Added `JanusSystemChrome`, reusing the existing `theme_mode` and `accent` SharedPreferences rather than creating a second appearance system.
- Default/slate chrome is dark neutral grey in dark mode and neutral grey in light mode; indigo/teal/amber/violet accents generate intentionally muted system-bar variants.
- System chrome listens for `theme_mode`/`accent` preference changes and updates live from Settings.
- Android manifest now explicitly enables `android:enableOnBackInvokedCallback="true"` at application and MainActivity level so the existing JANUS predictive-Back handler is not allowed to fall through silently on supported Android versions.
- Existing Back semantics remain: detail/subpage -> its explicit `← Options` parent; Messages/Observe/Options -> Chat; Chat -> Activity exit.
- Replaced the Runtime Cores map renderer with a hardware-safe implementation: no forced software layer, no shadows, simple lines/rounded boxes, dimension guards, and a catch/fallback renderer so a drawing failure cannot take down the Activity.
- v1.06 thought bridge and active Fano attention remain untouched.
- Android advances to versionName 1.07 / versionCode 107.

## v1.07 release rule
Do not merge until:
1. system-chrome, manifest Back enablement and CoreMap hardening regression gate passes;
2. v1.06 thought/Fano regression gate remains green;
3. v1.04 Chat performance regression gate remains green;
4. maintenance/auth/protocol/UI hardening checks remain green;
5. authoritative Java compilation succeeds;
6. APK assembly succeeds;
7. after merge, verify `apk-download` records `Publish JANUS Android native v1.07`.

## Required v1.07 real-device validation
- Dark/default theme: status and Android navigation-bar unused areas should be grey rather than white.
- Change accent in Settings: system chrome should update to a muted matching colour without requiring a reinstall.
- On a detail screen such as Activity or Cores, Android Back should return to Options; Back from Options should return to Chat; Back from Chat should exit.
- Open Runtime Cores repeatedly, background/foreground JANUS, and verify no Android app-bug report or Activity termination occurs.
- Reconfirm Chat can report actual between-message local processing and that typing remains responsive.
