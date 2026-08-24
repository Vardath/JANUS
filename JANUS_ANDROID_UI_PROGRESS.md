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

Implemented and published:
- selectable JANUS response text;
- Copy and Share response actions while retaining Report;
- delivery/offline System cards shown as delivery status;
- improved attachment-chip presentation;
- framed generated-image presentation;
- tappable URLs and improved long-response spacing;
- v0.83 safe-area protections retained.

## v0.85 — Cores and Observe architecture presentation

Implemented and published:
- dedicated native `JanusCoreMapView` showing the permitted 7 -> 2 -> 1 -> 1 forward topology;
- seven named specialist nodes, two hemispheres, Consensus and Interface;
- Safety visibly advises both hemisphere paths;
- explicit forward-only / feedback-through-specialist-review explanation;
- Local JANUS and Global JANUS runtime cards are visually distinct;
- Fano directions translated to human-facing processing orientations: Neutral, Grounding, Structure, Synthesis, Alternative, Continuity, Novelty, Boundary;
- Fano orientation remains explicitly labelled as processing orientation, not a truth score;
- Observe local/global records are visually distinguished;
- Observe retains stable non-auto-jumping snapshots and refreshes only by user choice.

## v0.86 — product-surface readability

Implemented and published:
- Options entries reorganized into JANUS, Research, System, App and Account-oriented labels;
- Memory distinguishes local continuity from durable global continuity and humanizes trace/working/episodic/core tiers;
- Research category headings are human-readable while preserving epistemic separation;
- System Status cards visually distinguish Healthy, Reduced capability and Needs attention;
- local background cadence uses Active, Balanced, Battery saver and Low activity labels;
- Maintenance clearly states that JANUS may recommend maintenance but cannot edit/deploy itself.

## v0.87 — Messages/Auth usability + authenticated route hygiene

Implemented on the v0.87 integration branch; release verification pending:
- new `JanusRoutePolicy` centralizes account-owned Android API path policy;
- authenticated requests strip obsolete `username`, `profile_id` and `user` query ownership hints for account-owned routes while preserving operational filters such as `limit` and `mode`;
- `JanusApiClient` applies route sanitization consistently to authenticated JSON requests and downloads;
- Messages uses clearer New-state emphasis and human-readable Question / Warning / Conclusion / Research finding / Maintenance / Suggestion / Follow-up labels;
- `Answer in Chat` is presented as `Reply in Chat`, and `Read` as `Mark read`;
- authentication copy is shorter and clearer while preserving the distinction between Google identity and JANUS-owned continuity;
- destructive account actions are visually differentiated;
- common loading/error text is made less developer-like;
- CI now gates route hygiene, Messages/Auth presentation, all prior safe-area/Chat/Cores/Observe/product invariants, and Java/APK compilation.

## Next intended passes

1. Continue internal code separation: progressively move screen state, endpoint definitions and feature-specific presentation out of monolithic `MainActivity` while preserving behavior.
2. Improve Messages reply context, Account/session presentation, Memory search/filtering and Research evidence/source cards where server contracts allow it safely.
3. Repository continuity/CI consolidation once Android product UI is stable.

Do not mark an Android pass fully released until the `apk-download` branch publishes the matching version after CI compilation and APK assembly.
