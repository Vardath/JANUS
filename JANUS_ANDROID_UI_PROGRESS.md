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

## v1.05 — Android Back semantics + local background-activity bridge
### Device-observed failures
1. Android system Back exited the Activity because JANUS swaps one native content container rather than using Android Fragments/Activities with a native back stack.
2. The local 11-core runtime was visibly performing deterministic background cycles, but Chat could still answer that JANUS had not been thinking while away because the server-facing conversational request did not receive the device runtime's persisted externalizable state.

### Implementation on `android-v105-navigation-thought-bridge`
- `JanusNavigationPolish` translates Android Back into JANUS navigation: explicit child/subpage back button first, then non-Chat top-level page -> Chat, then Activity exit from Chat.
- `JanusThoughtBridge` reads the persisted local runtime status/events and builds bounded background-activity context only for explicit questions about what JANUS was thinking/doing/processing while the user was away.
- Context explicitly describes deterministic local processing and zero model/API calls; it forbids presenting the data as uninterrupted private consciousness or phenomenal experience.
- Thought context is injected inside `JanusApiClient.postRaw()` at the authenticated `/desktop/chat` transport boundary, not into the visible composer. User bubbles and structured history therefore retain exactly the message the user typed.
- The abandoned composer-injection prototype was deleted before release.
- Android version advances to 1.05 / versionCode 105.
- v1.04 anti-spam/debounce gates remain mandatory.

## v1.05 release rule
Do not merge until:
1. navigation/thought-bridge static regression gate passes;
2. v1.04 UI performance regression gate remains green;
3. maintenance/auth/protocol checks remain green;
4. authoritative Java compilation succeeds;
5. APK assembly succeeds.
After merge, verify `apk-download` records `Publish JANUS Android native v1.05`, then perform real-device validation of Back navigation and an away/background-processing question.

## After v1.05
Continue reducing `MainActivity` responsibilities and improve wider-screen/tablet layouts after the navigation and thought bridge are verified on-device.
