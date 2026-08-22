# JANUS Deferred / Remaining Feature Registry

Updated: 2026-08-23

This file replaces the older deferred roadmap, which had become stale because several items originally listed as future work are now implemented on the server.

## Implemented since the original roadmap

The following are no longer deferred:

- authenticated account-bound file storage and deletion controls;
- document extraction/indexing and reusable grounding;
- selective vision-model escalation with cached results and cost governance;
- foreground one-shot image generation with bounded budgets;
- visual-explanation decision gating;
- multi-core visual-deliberation scaffolding with autonomous rendering disabled;
- outbound JANUS working artifacts such as continuity reports, research digests and project snapshots;
- research workspace with explicit epistemic categories;
- 90-day maintenance proposal generation and owner notification workflow;
- selective federated local/global synchronization with provenance/conflict preservation;
- memory-quality retrieval across retained history;
- background-usefulness suppression and cost/failure degradation;
- owner-facing server observability.

## Remaining Android product integration

These are active Phase 3 items rather than speculative future architecture:

1. Add a native Android file/image picker and upload UX that uses the existing attachment API.
2. Show uploaded files/images and attachment grounding clearly in Chat, including delete/remove controls.
3. Expose generated JANUS artifacts in Android with open/download/share actions.
4. Expose the research workspace in readable epistemic categories.
5. Expose maintenance proposals and owner approve/defer/reject controls in Android.
6. Expose useful autonomous research and provenance rather than only raw core telemetry.
7. Add explicit client/server protocol capability negotiation and graceful old-client degradation.
8. Harden and consolidate the Android build/patch path and add UI-level regression checks.

See `JANUS_PHASE3_PRODUCTIZATION.md` for the ordered implementation plan.

## Still deliberately deferred

### Windows/PC and Apple/iOS parity

Windows and Apple client parity remain deferred for now. Server protocol work should remain portable so those clients can catch up later without requiring a server redesign.

### Autonomous background image rendering

JANUS may discuss visual concepts in the background, but autonomous background rendering remains disabled. A later revenue/cost review may enable bounded rendering only after explicit policy, budget and user-permission work.

### Multi-render recursive art loops

The future concept → render → inspect → critique → revise loop remains intentionally inactive. The current visual-deliberation layer can reason over concepts, but actual iterative paid rendering should not be enabled until economically justified and tightly capped.

## Persistent boundaries

- No uncontrolled autonomous paid loops.
- No remote whole-state overwrite of local or global JANUS state.
- Protected identity/core state cannot be replaced by synced client records.
- Vision/image/model results are evidence, not automatic truth.
- Explicit user requests have priority over optional background spending.
- Hidden chain-of-thought is not exported as a product feature; only externalizable records, summaries, observations and artifacts are persisted or displayed.
