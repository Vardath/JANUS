# JANUS next-session checkpoint — 2026-08-23

This file is the authoritative handoff for the next implementation session.

## DECISION: stop patching the Android product; rebuild it cleanly

After reviewing the current repository state and the repeated Android build/runtime failures, the next Android direction is a clean **v0.80 rebuild** rather than continued stacked patching of the v0.69/v0.70/v0.71 client.

The server and JANUS cognition/core architecture are **not** being discarded. Preserve the working server, persistence, account ownership, memory, synchronization, research, attachment grounding, image policy, maintenance policy, and 11-core deliberation architecture. The rewrite is the Android presentation/runtime client and its build/test path.

Reason: the Android repository has accumulated competing implementation strategies. Some current tests/workflows expect a hard-coded consolidated Android product while other Phase 3 tests still require the older composer/patch pipeline. Version expectations also span v0.70 and v0.71. Continuing to patch this stack is now more expensive and less reliable than constructing one authoritative client source tree.

## Architecture invariants to preserve

JANUS remains the experimental functional-metacognition/agency system, not a claim of phenomenal consciousness.

Preserve the established **7 specialist → 2 hemisphere → Consensus → Interface** topology (11 active cores total; visible shorthand 7→2→1→1).

Preserve:
- authenticated account/profile ownership; never trust a client-selected username for private state;
- protected identity/core state that ordinary conversation/sync cannot overwrite;
- selective, provenance-preserving local/global synchronization rather than whole-state overwrite;
- persistent continuity and memory promotion/retrieval/consolidation;
- local-device and server/global activity as distinct states;
- bounded background/sleep cycles and cost controls;
- graceful provider/network degradation and offline queueing;
- foreground Chat remaining usable when optional background budgets are exhausted;
- maintenance may propose upgrades/reviews but may not self-modify without owner approval;
- medium-quality user-requested/occasional explanatory image generation, while autonomous background core image generation remains deferred/economically gated;
- real live-web/YouTube research through the server, with provenance and no fabricated retrieval claims.

## Known-good server capability to retain

The live web boundary was successfully crossed before the Android client became unstable. Normal Android JANUS Chat demonstrated Android → JANUS server → foreground web research → returned web/YouTube evidence → Interface response. Preserve that bridge rather than redesigning it without evidence of a server failure.

The server should continue to support direct/public URL ingestion, indexed web/YouTube search, transcript/caption retrieval where available, truthful fallback when unavailable, caching/provenance, attachment upload/grounding, account isolation, generated artifacts, and JANUS deliberation routing.

## Android v0.80 rebuild goal

Create a new Android client alongside the existing client until the replacement is proven. **Do not delete the old client first.** It remains a reference/rollback source while v0.80 is built.

The v0.80 rule is simple: **one authoritative Android source tree, one authoritative build path, one release gate.**

Do not make the production application depend on sequential Python scripts rewriting generated HTML/Java/Kotlin at build time. Existing patch/composer scripts may be retained temporarily under legacy/reference status so useful implementation details are not lost, then retired after v0.80 reaches feature parity.

Tests must test the real authoritative app/API contract rather than infer product correctness by checking whether old patch scripts contain particular strings.

## Required v0.80 feature parity

Reimplement the existing intended product features coherently:

1. Account creation/login/password flows and existing Google authentication support; retain Apple-facing capability for later platform parity where applicable.
2. Main Chat with reliable send/reply, markdown/readability, source/provenance presentation, report controls and resilient network behavior.
3. Messages/queued JANUS prompts.
4. Observe view for readable specialist/core activity without rapid-refresh usability problems.
5. Options and System Status, including human-readable Healthy / Reduced capability / Needs attention reporting.
6. Visible 11-core / 7→2→1→1 architecture and appropriate per-core telemetry/log views.
7. Local/offline message queue with bounded retry and no duplicate user-message rendering.
8. Native file attachment picker, authenticated upload, visible chips, removal, four-file turn limit, attachment IDs in Chat, server grounding/vision/extraction and provenance.
9. Native generated-file open/download/share/export workflow.
10. Research workspace separating proven mathematical results, hypotheses, negative results, open questions, evidence and proposed tests.
11. Live web, public URL, YouTube/channel/video/transcript research through the working server bridge.
12. Background research/provenance UI showing completed research, sources, suppression reasons and external-compute use.
13. Maintenance/upgrade proposal UI with approve/defer/reject; roughly 90-day review concept; no autonomous self-modification.
14. Interface themes/colour settings as client settings rather than cognition state.
15. Background/sleep-cycle controls and local core telemetry consistent with the federated local/global design.
16. Protocol/capability negotiation so the client can truthfully know which server capabilities are available.
17. Existing JANUS continuity/memory/account semantics and selective sync behavior.

## v0.80 implementation sequence

### Stage 0 — freeze and map
Before writing replacement UI code, inventory the current server API and current Android-visible features. Establish a v0.80 client/server contract. Do not casually alter server endpoints merely to fit the new client.

### Stage 1 — clean shell + auth + connectivity
Create the new authoritative Android project/client shell. Implement account/login/session persistence, server health/capability negotiation, navigation, and a minimal reliable Chat transport.

Acceptance: app launches reliably, controls respond, auth persists correctly, health is truthful, and a basic Chat round trip succeeds.

### Stage 2 — Chat resilience + local queue
Implement message state, send lifecycle, offline/timeout queue, bounded retry, deduplication, reconnection and readable failure states.

Acceptance: no frozen blank Chat, no duplicate queued message bubbles, no uncontrolled retry loop, and queued messages recover after connectivity returns.

### Stage 3 — Messages + Observe + Options/System Status
Rebuild the primary UI surfaces directly rather than importing patched HTML behavior. Observe must remain readable/stable and must not visually refresh itself into unusability.

### Stage 4 — attachments + native file handling
Implement pick → authenticated upload → chip → send → server grounding/vision/extraction → provenance, plus generated artifact open/share/export.

### Stage 5 — research product surfaces
Connect live web/URL/YouTube/transcript research, Research workspace, source/provenance rendering, background research records and generated research artifacts.

### Stage 6 — maintenance, themes and background controls
Add maintenance approval UI, themes, sleep/background controls and remaining user options without mixing them into protected server cognition state.

### Stage 7 — feature parity audit
Compare v0.80 against the old client and the Phase 2/3 project documentation. Any useful feature not intentionally deferred must either be implemented or explicitly documented before retirement of the old client.

### Stage 8 — CI/release simplification
Replace contradictory Android checks with a small coherent matrix: compile/build the actual app, unit/API-contract tests, focused UI/instrumentation smoke tests, and one release gate. Keep server tests separate where appropriate.

### Stage 9 — known-good APK
Only after the v0.80 gate is green, produce the APK, test it on the real Android device, verify login/chat/web/attachments/Observe/options/offline recovery, then designate v0.80 as the new baseline. Archive/retire the old patch pipeline only after this point.

## Immediate next-session task

Start with **Stage 0**, not another Android patch. Review:
- this checkpoint;
- `JANUS_PHASE3_PRODUCTIZATION.md`;
- `JANUS_PROJECT_MEMORY.md`;
- current server routes/API models;
- current Android authoritative/hard-coded source;
- current patch/composer scripts only as a feature/reference inventory;
- current tests and GitHub Actions workflows.

Produce the v0.80 feature/API map, identify what can be reused unchanged, then create the clean client alongside the existing one.

## CI cleanup rule

Do not spend another session making contradictory legacy assertions agree with one another unless a check protects a genuine server/product invariant. During the parallel rebuild, clearly distinguish **legacy-client checks** from **v0.80 checks**. The v0.80 release gate becomes authoritative only when feature parity and device validation are complete.

## Deferred / economic gates

- Windows/PC parity and Apple/iOS parity remain deferred until explicitly resumed.
- Autonomous visual candidate render/inspect/revise loops remain revenue/cost gated.
- Deeper image communication between background JANUS cores remains future work after economics/cost controls justify it.
- Unbounded autonomous YouTube/channel crawling is not part of the baseline.

## Working method

Preserve successful server/core work and fix server failures forward when genuine server failures are observed. For Android, stop stacking production patch scripts and build v0.80 coherently.

After every implementation commit, provide the GitHub Actions page link so the owner can immediately inspect the current-head runs. Judge the current commit/run, not historical red runs.

## Most important state to remember

**Next session begins the clean JANUS Android v0.80 rebuild. Keep the working JANUS server/core architecture. Build the replacement alongside the old client, reach feature parity in controlled stages, simplify CI to test the real product, validate a known-good APK on-device, and only then retire the legacy patch/composer Android pipeline.**
