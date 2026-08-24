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

## v0.95 — persistent structured Chat metadata + controller extraction foundation
Implemented on integration branch; release verification pending:
- `JanusChatPresentation` now serializes/deserializes reply, source and generated-image metadata;
- `JanusChatResponseRegistry` is bounded to 16 entries and persists structured presentation records across app restarts;
- `JanusApplication` initializes that registry at process startup, so saved JANUS messages can regain source/image metadata after relaunch;
- new `JanusChatController` centralizes the intended retry schedule, response parsing and failure classification for the next MainActivity migration step;
- the current MainActivity send loop remains the live sender in this pass; the controller is deliberately introduced and compile-gated before the risky final wiring, rather than pretending the monolithic Activity has already been removed;
- no server, cognition, federation, auth ownership or 11-core routing contract changed;
- CI requires persistent registry initialization/storage, Chat presentation serialization, controller compilation, structured source rendering, safe insets, reply context, route hygiene, forward-only core routing, Java compilation and APK assembly.

## Next intended passes
1. Switch `MainActivity.sendChat()` onto `JanusChatController` and remove the duplicate retry/response-parse block from the Activity.
2. Remove the live `formatSources()` compatibility append from Chat, leaving it only for non-Chat legacy/background-research formatting or replacing that use too.
3. Move saved Chat history itself to structured records and continue separating Messages/Observe/Research surfaces.

Release rule: do not mark a pass fully released until `apk-download` publishes the matching version after CI compilation and APK assembly.
