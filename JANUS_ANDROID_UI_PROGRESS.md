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
- v0.99: structured history v2 became an independent bounded store with one-way legacy migration; completed migration build verified and published.

## v1.00 — structured Chat v2 is the visible surface authority
Implemented on integration branch; release verification pending:
- new `JanusChatV2Surface` watches the actual native Chat surface and projects authoritative v2 history into every newly-created Chat log before normal use;
- subsequent user/JANUS/system bubbles are captured back into the v2 store when the visible Chat log changes;
- the existing private `MainActivity.renderSavedChat()` is invoked only as a compatibility renderer after v2 has been projected, so `chat_history_native_v1` is now an adapter/migration surface rather than the durable source of truth;
- the v2 store remains the long-lived bounded source for clean reply text plus structured sources/generated-image metadata;
- application lifecycle installs the v2 surface authority and retains pause/stop/save capture as additional resilience;
- Android version advances to 1.00 / versionCode 100;
- no server, cognition, federation, auth ownership or 11-core routing contract changes;
- CI requires the v2 surface authority, one-way legacy migration, shared foreground/queued Chat controller path, structured source/image restoration, safe insets, reply context, route hygiene, forward-only core routing, Java compilation and APK assembly.

## Remaining Chat cleanup after v1.00
1. Replace the foreground Activity's duplicate retry/JSON/source-append block with direct `JanusChatController.send()` usage once a safe targeted source-edit path is available.
2. Remove `formatSources()` from foreground Chat completely; keep any Background Research formatting independent.
3. Retire the v1 compatibility adapter after a release window once v2-only history has been exercised on-device.
4. Continue extracting Messages/Observe/Research surfaces and wider-screen layouts.

Release rule: do not mark a pass fully released until `apk-download` publishes the matching version after CI compilation and APK assembly.
