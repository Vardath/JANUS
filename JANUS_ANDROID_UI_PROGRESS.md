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
- v0.98: foreground `/desktop/chat` API posts cross the shared controller boundary; structured history v2 introduced alongside legacy history. Verified published 2026-08-24.

## v0.99 — authoritative structured Chat history
Implemented on integration branch; release verification pending:
- `JanusChatHistoryStore` now treats `chat_history_native_v2` as the authoritative structured store instead of continuously mirroring legacy v1;
- existing v1 history is imported once, only when v2 is empty, preserving existing conversations without repeatedly overwriting structured records;
- new append/read/clear operations own schema-v2 history directly;
- JANUS records can carry serialized `JanusChatPresentation`, keeping clean reply text, sources and generated-image metadata attached to the saved message;
- history remains bounded to the most recent 80 records;
- the old SharedPreferences change-listener mirroring path is removed, preventing v1 from silently replacing richer v2 records;
- no server, cognition, federation, auth ownership or 11-core routing contract changed;
- CI verifies one-way migration, authoritative append API, structured presentation metadata, shared foreground/queued Chat boundaries, source/image persistence, safe insets, reply context, route hygiene, forward-only core routing, Java compilation and APK assembly.

## Next intended passes
1. Switch the visible Chat renderer/remember path in `MainActivity` to call the v2 read/append APIs directly, then retain v1 only as a migration source.
2. Remove the Activity-local live `formatSources()` append and duplicate response parsing; keep Background Research source formatting independent.
3. Continue extracting Chat/UI responsibilities from `MainActivity`, then return to Messages/Observe/Research and wider-screen polish.

Release rule: do not mark a pass fully released until `apk-download` publishes the matching version after CI compilation and APK assembly.
