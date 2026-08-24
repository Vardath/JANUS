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
- v1.00: structured Chat v2 became the visible surface authority; published APK verified.

## v1.01 — direct foreground Chat controller + v2 history
Pre-merge Android CI is green (gate, Java compilation, APK assembly):
- `MainActivity.sendChat()` now calls `JanusChatController.send(api, prepared)` directly; the Activity-local retry array/loop is removed;
- successful foreground replies use `JanusChatPresentation` as the authoritative reply/source/generated-image model;
- the live Chat bubble receives clean reply text only; the old foreground `Sources:` appendix construction is removed;
- Background Research retains a separate `formatResearchSources()` helper so research provenance formatting is independent from Chat rendering;
- foreground JANUS replies are persisted directly with `JanusChatHistoryStore.append(..., presentation)`;
- user/system bubbles use the v2 history append path through `rememberChat()`;
- `renderSavedChat()` reads `JanusChatHistoryStore.read()` directly and reseeds the presentation registry from each stored structured presentation so source cards/generated images remain available after restart;
- `JanusChatResponseRegistry.remember()` was added for authoritative-history reseeding and de-duplication;
- `JanusApplication` no longer installs the v1.00 reflective `JanusChatV2Surface` or lifecycle capture bridge in normal operation;
- legacy v1 history remains only as the one-way migration source inside `JanusChatHistoryStore` during the compatibility window;
- version advances to 1.01 / versionCode 101;
- no server, cognition, federation, auth ownership or 11-core routing contract changed;
- PR #13 pre-merge build successfully passed the v1.01 ownership gate, Java compilation and APK assembly before merge.

## Next intended passes
1. After v1.01 publishes, delete or quarantine the now-unused `JanusChatV2Surface` / `JanusChatHistoryBridge` compatibility classes after confirming no remaining references.
2. Preserve structured metadata for queued/offline replies rather than only their reply text.
3. Continue extracting Messages/Observe/Research surfaces from `MainActivity` and improve wider-screen/tablet layouts.
4. Add targeted regression tests around v2 history migration, reply-context send, source-card restoration and generated-image restoration.

Release rule: do not mark a pass fully released until `apk-download` publishes the matching version after CI compilation and APK assembly.
