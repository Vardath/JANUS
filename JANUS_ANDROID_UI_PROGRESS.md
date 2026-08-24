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
- v1.03: Messages and read-only Observe gained dedicated native screen owners; all pre-merge checks passed and the APK was published.

## v1.04 — Chat UI spam / typing-lag hotfix
### Device-observed failure
On a long Chat history, asking JANUS what it had been thinking about while away exposed a client rendering bug:
- a JANUS response accumulated Copy/Share rows repeatedly without stopping;
- the app progressively slowed;
- composer keystrokes became delayed;
- the Observe guide could appear on Chat near the bottom navigation.

### Root cause audit
1. `JanusUiPolish` used the ordinary single `View.setTag()` slot to remember that a Chat card had received Copy/Share controls.
2. `JanusSourcePolish` reused that same tag slot for its own structured-source marker, overwriting the Chat marker.
3. On the next global-layout callback, `JanusUiPolish` therefore believed the same JANUS card was unprocessed and appended another Copy/Share row. Repetition created unbounded view growth.
4. Four independent decorators (`JanusUiPolish`, `JanusSourcePolish`, `JanusGeneratedImagePolish`, `JanusReplyContextPolish`) performed recursive view-tree work from global-layout callbacks. With a long conversation this amplified UI-thread work during keyboard/composer layout changes.
5. Observe-guide title matching accepted `Button` because Android `Button` subclasses `TextView`; the bottom navigation button labelled `Observe` could be mistaken for the actual Observe page title.

### v1.04 remediation on `android-v104-ui-spam-fix`
- `JanusUiPolish` now uses weak identity sets (`CHAT_ENHANCED`, `BASE_POLISHED`, dedicated core-map/Observe-guide sets) rather than shared plain `View.setTag()` ownership markers.
- Copy/Share decoration is idempotent per Chat card.
- base styling is idempotent per View rather than rewriting properties on every pass.
- global-layout polishing is debounced so typing does not synchronously trigger a full recursive polish for every layout event.
- source, generated-image and Reply-in-Chat scanners are independently debounced.
- source decoration uses a weak `ENHANCED` set and no longer overwrites Chat-decoration ownership.
- Observe/core-title matching excludes `Button` instances, preventing navigation labels from being treated as page titles.
- Android version advances to 1.04 / versionCode 104.
- UI-hardening tests and the Android build gate explicitly reject return of the shared-tag Chat marker and require the debounce/idempotence protections.

## Release rule for v1.04
Do not merge or publish until:
1. UI hardening regression tests pass;
2. existing maintenance/auth/protocol gates pass;
3. authoritative Java compilation succeeds;
4. APK assembly succeeds;
5. after merge, `apk-download` records `Publish JANUS Android native v1.04`;
6. real-device validation confirms one Copy/Share row per JANUS message, no Observe guide on Chat, and responsive typing with a long history.

## Next intended work after the hotfix
Resume architecture cleanup only after v1.04 is stable on-device. Continue reducing `MainActivity` responsibilities and improving tablet/wide-layout behavior, but do not stack UI architecture work on top of an unverified performance regression.
