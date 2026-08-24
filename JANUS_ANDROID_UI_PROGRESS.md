# JANUS Android UI Improvement Progress

Updated: 2026-08-24

## Authoritative baseline

- Android product: native `android/` client only; no WebView/generated HTML/patch-composer product path.
- Production server: `server_v2/`.
- Runtime topology remains 7 specialists -> 2 hemispheres -> Consensus -> Interface.
- Preserve forward-only routing, feedback-only federation, stable Observe snapshots, zero-API deterministic local cycles, authenticated account ownership, and owner-gated maintenance.

## v0.83 — safe areas and native chrome

Implemented and published:
- system status-bar inset handling;
- Android navigation/gesture-bar bottom inset handling;
- IME/keyboard clearance using the larger of navigation-bar and keyboard insets;
- transparent system bars with theme-aware icon contrast;
- rounded native inputs, cards/surfaces and improved button/navigation presentation;
- app-wide treatment for dynamically rebuilt programmatic screens.

## v0.84 — Chat readability/actions

Implemented and build-verified:
- selectable JANUS response text;
- Copy and Share response actions while retaining Report;
- delivery/offline System cards shown as delivery status;
- improved attachment-chip presentation;
- framed generated-image presentation;
- tappable URLs and improved long-response spacing;
- v0.83 safe-area protections retained.

## v0.85 — Cores and Observe architecture presentation

Implemented on `main`; publication verification pending at the time of this checkpoint:
- dedicated native `JanusCoreMapView` showing the permitted 7 -> 2 -> 1 -> 1 forward topology;
- seven named specialist nodes, two hemispheres, Consensus and Interface;
- Safety visibly advises both hemisphere paths;
- explicit forward-only / feedback-through-specialist-review explanation;
- Local JANUS and Global JANUS runtime cards are visually distinct;
- Fano directions are translated to human-facing processing orientations: Neutral, Grounding, Structure, Synthesis, Alternative, Continuity, Novelty, Boundary;
- Fano orientation remains explicitly labelled as processing orientation, not a truth score;
- Observe local/global records are visually distinguished;
- Observe retains stable non-auto-jumping snapshots and explicitly tells the user refresh occurs only by choice;
- CI gates the architecture map, Fano labels, local/global distinction, stable snapshot wording, prior Chat actions and safe-area invariants before compilation.

## Next intended passes

1. Options/navigation hub, Memory, Research, System Status and Maintenance human-readable cleanup.
2. Internal code separation: progressively move screen/API responsibilities out of the monolithic MainActivity while preserving behavior.
3. Repository continuity/CI consolidation once product UI is stable.

Do not mark an Android pass fully released until the `apk-download` branch publishes the matching version after CI compilation and APK assembly.
