# JANUS Android UI Improvement Progress

Updated: 2026-08-24

## Authoritative baseline
- Native `android/` client only; no WebView/generated HTML/patch-composer product path.
- Production server: `server_v2/`.
- Runtime topology: 7 specialists -> 2 hemispheres -> Consensus -> Interface.
- Preserve forward-only routing, feedback-only federation, stable Observe snapshots, zero-API deterministic local cycles, authenticated account ownership, and owner-gated maintenance.

## Verified published passes
- v0.83: Android status/navigation/IME safe areas and native chrome.
- v0.84: Chat readability, selectable responses, Copy/Share/Report, delivery and attachment/image polish.
- v0.85: Cores/Observe 7->2->1->1 presentation, Local/Global distinction, readable Fano modes, stable snapshots.
- v0.86: Options/Memory/Research/System/Settings/Maintenance product readability.
- v0.87: Messages/Auth usability and authenticated route hygiene.
- v0.88: screen-state extraction and loading/empty/failure presentation.
- v0.89: Memory filtering/search, Research evidence presentation, Account session/security presentation.
- v0.90: Messages Reply-in-Chat context card with context retained in outgoing payload.
- v0.91: tappable Chat source cards and consolidated less-brittle Android CI gate.
- v0.92: immutable `JanusChatPresentation` model plus adaptive/accessibility layer and 48dp touch targets.
- v0.93: source-card renderer accepts structured source records directly.
- v0.94: live structured source handoff captured at the API boundary and matched to rendered Chat responses.
- v0.95: persistent structured reply/source/generated-image metadata and Chat controller foundation.
- v0.96: controller-owned raw `/desktop/chat` transport primitive (`postRaw`) separated from the general API response-capture path.
- v0.97: queued delivery moved onto the shared Chat controller/API stack; generated-image metadata restored after restart.

## v0.98 — foreground controller boundary + structured history v2
Implemented on integration branch; release verification pending:
- ordinary authenticated `JanusApiClient.post("/desktop/chat", ...)` calls now cross `JanusChatController.sendOnce()` before returning to the foreground Activity, so foreground and queued Chat share the same response parsing/presentation-capture boundary;
- the existing `MainActivity.sendChat()` outer retry loop is retained temporarily, avoiding nested retry storms while the giant Activity is progressively extracted;
- new `JanusChatHistoryStore` maintains `chat_history_native_v2` structured records alongside the legacy visible history during migration;
- the store listens for legacy Chat-history changes and immediately mirrors the last 80 records into schema-v2 entries;
- JANUS records attach the matching serialized `JanusChatPresentation` when available, preserving sources and generated-image metadata directly with the saved message rather than only in a bounded side registry;
- the visible body stored in v2 is the clean JANUS reply when structured presentation is available, not the old flattened `Sources:` appendix;
- `JanusApplication` installs the structured history store at startup;
- legacy `chat_history_native_v1` remains readable by `MainActivity` in this pass, so the migration is backward-compatible and does not risk blanking existing conversations;
- no server, cognition, federation, auth ownership or 11-core routing contract changed;
- CI requires foreground Chat routing through the controller boundary, structured-history v2/listener/presentation metadata, queued controller delivery, persistent source/image rendering, safe insets, reply context, route hygiene, forward-only core routing, Java compilation and APK assembly.

## Next intended passes
1. Switch `MainActivity` rendering/remembering to structured history v2 so the legacy `who/body` history can be retired after a compatibility window.
2. Remove the Activity-local live `formatSources()` append and duplicate response parsing once a safe source-level edit path is used; keep Background Research source formatting independent.
3. Continue separating Messages/Observe/Research surfaces and wider-screen layouts after the Chat boundary is clean.

Release rule: do not mark a pass fully released until `apk-download` publishes the matching version after CI compilation and APK assembly.
