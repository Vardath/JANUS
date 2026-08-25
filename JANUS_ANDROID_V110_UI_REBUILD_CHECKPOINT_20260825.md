# JANUS Android v1.10 UI rebuild checkpoint — 2026-08-25

## Completed first milestone: app-only appearance

Android v1.10 fixes the theme-boundary bug discovered on the real Samsung device.

- `theme_mode` and `accent` remain JANUS application preferences used by JANUS-owned rendering.
- JANUS no longer recolours Android status or navigation bars from those preferences.
- `JanusSystemChrome` now only aligns system-bar icon contrast to the device's own current light/dark configuration.
- The change was merged in PR #45 at `edb3f1f5b00153da0f572cff54057fb16f37c058`.
- The authoritative Android APK build, Android UI hardening, RC readiness, auth, protocol, recursive-core and maintenance gates passed for the PR head before merge.

This is a scope correction, not cosmetic polish: JANUS appearance controls must never alter the host phone's global/system appearance.

## Important v1.09 stability-shell finding

The v1.09 crash-isolation pass intentionally stopped installing several runtime UI polish/injection layers. Two older CI contracts still expected those layers to be installed:

1. Stream observation expected `JanusStreamObservePolish.install(...)`.
2. Localization expected `JanusUiLocalizationPolish.install(...)`.

Those failures are not a reason to restore the old injection stack. They expose unfinished UI migration work.

The old Stream implementation uses delayed view-tree searching plus reflection into `MainActivity` fields. That pattern is now deprecated for product integration because it conflicts with the screen-owned/deterministic-rendering direction.

## Explicit Stream owner begun

`JanusStreamScreen` is the replacement screen-owned renderer. It:

- receives its host dependencies explicitly;
- receives the content container explicitly;
- performs no live view-tree search;
- performs no private-field reflection;
- installs no delayed or global-layout callback;
- remains read-only and externalizable-only;
- reads local Front recursive state and `/desktop/stream-observe` global Front state;
- preserves the rule that hidden chain-of-thought is never exposed.

It is intentionally not activated through the old injector. The remaining integration step is to make Stream a first-class navigation/page route owned directly by the native activity/screen hierarchy.

## Immediate next UI work

1. Wire `JanusStreamScreen` into explicit native navigation without reflection or view-tree injection.
2. Move localization from the disabled global UI-localization injector into deterministic screen/component ownership; preserve the existing translation catalogue and English fallback.
3. Remove hard-coded visible version text such as `Options · v1.09 (109)` and source it from `BuildConfig` or a single authoritative version helper.
4. Continue simplifying readability and navigation while keeping JANUS controls spatially separate from Android/system controls.
5. Keep safe-area handling, predictive/system Back, accessibility, Chat history, Messages, Observe, diagnostics and maintenance governance intact.
6. Real-device test Cores, Memory, Settings, Stream, Messages, Observe and Options after each major integration step.
7. If a detail screen still closes, expose the stored `JanusClientDiagnostics` crash report in-app with copy/share support and fix from the exact stack trace.

## Architecture invariants to preserve

- 11 local + 11 global top-level cores.
- Every top-level core remains a complete seven-faculty JANUS/Fano processor.
- Outward route remains `seven specialists -> Left + Right -> Front -> Interface -> user`.
- Interface receives Front only.
- Rest remains passive; foreground input can rouse immediately.
- Deterministic recursive background processing remains zero-model/API-call.
- Peer processing remains bounded and quiescent when state is unchanged.
- Maintenance remains owner/Supervisor gated and append-only for unresolved requests.

## After UI stability

Resume Diagnostic System v2 behavioral proof, then real-device soak testing, then Android release-candidate hardening.
