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
- v0.93: source-card renderer accepts structured `JanusChatPresentation.Source` records directly rather than parsing a text appendix.

## v0.94 — live structured Chat source handoff
Implemented on integration branch; release verification pending:
- `JanusApiClient` captures successful `/desktop/chat` response JSON at the HTTP boundary before `MainActivity` flattens any source metadata;
- new bounded `JanusChatResponseRegistry` converts that response immediately into `JanusChatPresentation` and retains only a small in-process recent queue;
- `JanusSourcePolish` matches a rendered JANUS reply to its captured structured presentation, replaces the visible body with the clean reply, and builds source cards from the original structured source records;
- source title/domain/URL therefore come from server JSON rather than reparsing the rendered `Sources:` appendix;
- legacy `formatSources()` remains inside `MainActivity` only as a compatibility/persistence fallback while the monolithic Activity is progressively extracted; it is no longer the data source used by the v0.94 source-card renderer;
- no server, cognition, federation, auth ownership or 11-core routing contract changed;
- CI requires API-boundary capture, registry handoff, structured source rendering, safe insets, reply context, route hygiene, forward-only core routing, Java compilation and APK assembly.

## Next intended passes
1. Extract the Chat network/send controller from `MainActivity` so the legacy `formatSources()` compatibility append can be removed entirely rather than merely bypassed for presentation.
2. Move saved Chat history to a structured record that can retain source metadata and generated-image metadata across app restarts.
3. Continue separating Messages/Observe/Research surfaces and improve larger-screen layouts once the live Chat controller is independent.

Release rule: do not mark a pass fully released until `apk-download` publishes the matching version after CI compilation and APK assembly.
