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

## v0.97 — shared queued Chat delivery + persistent generated images
Implemented on integration branch; release verification pending:
- `JanusChatController` now exposes `sendOnce()` for WorkManager/offline delivery while retaining its bounded foreground retry policy;
- `JanusOfflineQueue` no longer maintains a second raw `HttpURLConnection` Chat client: queued messages now use `JanusApiClient` + `JanusChatController.sendOnce()`;
- worker scheduling remains responsible for later queue retries, avoiding nested retry storms;
- `JanusChatResponseRegistry` adds non-destructive `findForReply()` so source and image renderers can share the same persisted structured presentation;
- new `JanusGeneratedImagePolish` restores generated images from persisted `generated_image.file_id` metadata, including after process/app restart, with accessibility descriptions and duplicate protection;
- `JanusApplication` installs the generated-image restoration layer alongside structured sources, reply context, safe-area and adaptive UI layers;
- no server, cognition, federation, auth ownership or 11-core routing contract changed;
- the large foreground `MainActivity.sendChat()` method is still the remaining direct sender and is explicitly NOT claimed as migrated in this pass;
- CI rejects a return of raw `HttpURLConnection` logic inside `JanusOfflineQueue` and verifies controller delivery, image restoration, structured sources, safe insets, reply context, route hygiene, forward-only core routing, Java compilation and APK assembly.

## Next intended passes
1. Replace the remaining foreground `MainActivity.sendChat()` networking/retry/parser block with `JanusChatController.send()` using a safe source-level edit, then remove the duplicate Activity retry policy.
2. Remove the live Chat `formatSources()` compatibility append completely; retain/replace the separate Background Research formatter independently.
3. Move Chat history from plain `who/body` records to structured message records so source/image/reply metadata is attached directly to each saved message rather than matched through a bounded registry.
4. Continue separating Messages/Observe/Research surfaces and wider-screen layouts after the Chat boundary is clean.

Release rule: do not mark a pass fully released until `apk-download` publishes the matching version after CI compilation and APK assembly.
