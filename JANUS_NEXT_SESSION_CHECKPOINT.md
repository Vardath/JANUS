# JANUS next-session checkpoint — 2026-08-23

This file is the authoritative handoff for the next implementation session.

## Current baseline

Phase 2 stabilization is complete. Phase 3 Android/server productization is active. The current Android baseline remains v0.69/v0.70-era Phase 3 work, with Windows/PC and Apple/iOS parity still intentionally deferred.

JANUS remains the experimental functional-metacognition/agency system with the established **7 specialist → 2 hemisphere → Consensus → Interface** topology. This is not a claim of phenomenal consciousness.

Preserve these invariants:
- authenticated account/profile ownership; never trust a client-selected username for private state;
- server and local-device activity are distinct and must be reported separately;
- local/global synchronization is selective and provenance-preserving, never a whole-state overwrite;
- protected identity/core state cannot be overwritten by ordinary conversation/sync state;
- memory retrieval should recover relevant older conversation, prioritize corrections, consolidate duplicates and retain continuity cues;
- background research remains bounded by usefulness/repetition gates and cost controls;
- provider failures degrade gracefully and failed provider calls do not consume estimated-success budget;
- foreground Chat remains available when optional background budgets are exhausted;
- image generation remains bounded and user-requested/foreground; uncontrolled autonomous/background rendering stays disabled;
- maintenance may propose upgrades/reviews but JANUS must not self-modify without owner approval.

## Phase 2 work present

The repository retains the completed stabilization work: route/security inventory and profile-boundary hardening; persistence/migration matrix and schema preflight; background usefulness audit; memory-quality retrieval; server/local synchronization soak; cost/failure degradation handling; owner-facing observability; Android System Status UI; and release-checkpoint coverage.

Owner observability should translate telemetry into useful English and distinguish Healthy / Reduced capability / Needs attention. Android exposes this under Options → System status.

## Attachment feature status

The Android Chat attachment feature was previously found to have regressed from the authoritative build path even though the implementation still existed. It was restored by applying `tools/patch_android_file_attachments.py` before the consolidated runtime patch. The visible `+` attachment button was later confirmed in a live Android screenshot.

Preserve attachment support and keep regression coverage for:
- native picker callback;
- authenticated upload;
- visible attachment chips;
- four-attachment-per-turn limit;
- removal before send;
- attachment IDs passed into Chat;
- server-side grounding/vision/extraction provenance.

Do not revert later Android/core/sync/Observe/System Status work to restore attachments.

## Major progress completed today — live web and YouTube research

The earlier research/browser gap is now substantially closed.

### What was wrong

Several independent problems were found across the day:
1. Interface/diagnostic wrappers were answering internet/YouTube questions from telemetry before the research path could run.
2. Short follow-ups such as “check again” inherited diagnostic intent instead of research intent.
3. `curiosity_search.py` did not reliably classify YouTube/transcript/browser/connectivity language as foreground web research.
4. The foreground OpenAI research call was configured in a way that could perform a web tool call but return no final textual result, producing `empty_web_result`.
5. Model/runtime configuration was inconsistent between product-facing names and API-facing model identifiers.
6. Even after the diagnostic endpoint worked, the normal Chat route still bypassed the successful web bridge.

### Fixes now present

The fixes were made forward without reverting successful Phase 3 work. Key recent commits included the sequence culminating in the normal-chat fix:
- `3b42bc7` — hard-coded foreground classification for internet/YouTube/transcript/browser/current-data requests;
- `dab1351` — live research diagnostic and more robust web-runtime handling;
- `9b417dd` — corrected web-search completion/extraction behavior;
- `3c5874e` — final normal Chat routing fix so explicit live-web/YouTube requests reach the working foreground bridge instead of telemetry wrappers.

The authoritative behavior now is:
- explicit web/internet/current-data requests invoke foreground web research;
- YouTube search requests can search indexed public YouTube material;
- direct public URLs still go through the URL/media ingestion layer;
- YouTube video URLs attempt transcript/caption retrieval when available, with no-fabrication fallback to title/description/indexed evidence;
- retrieved material is intended to route through the Evidence/Logic/Counterpoint/Context/Memory/Novelty → hemispheres → Consensus → Interface fabric;
- chat must distinguish actual retrieval failure from “no tool exists”;
- telemetry is never sufficient evidence to claim internet capability either works or fails.

### Live verification completed

A live Render diagnostic successfully returned:
- `web_attempted: true`
- `web: true`
- `retrieved: true`
- `actual_model: "gpt-5.6"`
- a real current-result payload
- `error: null`

This proved the server-side web bridge was actually reaching live search rather than merely reporting configured capability.

After the final normal-chat routing fix, a live Android screenshot confirmed that the regular JANUS Chat interface itself now reports **“Internet and YouTube access confirmed”** and returns:
- an actual OpenAI newsroom web result;
- an indexed YouTube channel/video result;
- retrieved source URLs;
- truthful capability limits for public/indexed versus private/unlisted content.

Treat this as the first successful end-to-end proof of:
**Android Chat → JANUS server → foreground live web research → returned web/YouTube evidence → normal JANUS Interface response.**

This is no longer just a diagnostic-endpoint success.

## Remaining research/browser follow-up

The core live-web boundary is now crossed, but the research layer still needs hardening rather than more basic connectivity work.

Next research tasks:
1. Test real user-relevant channel discovery against **Black Sheep Researcher** and **Jeff Snyder2**.
2. Test direct YouTube video URLs for transcript/caption retrieval, including:
   - transcript available;
   - captions unavailable;
   - blocked/private/unlisted;
   - title/description-only fallback.
3. Confirm bounded channel enumeration can discover a small relevant/recent video set rather than only generic web-index results.
4. Keep canonical URL/content caching so repeated analysis does not repeatedly spend model/web budget.
5. Preserve source URL, video title, retrieval time, transcript availability and provenance in stored research notes.
6. Confirm retrieved material genuinely passes through the specialist/hemisphere/Consensus fabric before Interface response, rather than becoming a direct unexamined scrape.
7. Improve source extraction/provenance formatting where needed so every factual live-web answer can clearly identify what was actually retrieved.
8. Add/retain regression tests covering normal Chat routing, successful live web search, YouTube search, transcript fallback, no-fabrication behavior, caching, account isolation and provider failure degradation.

## Current Phase 3 order

The earlier Priority 1 URL/YouTube/live-web integration is now functionally successful and moves from “implementation gap” to **hardening/verification**.

### Priority 1 — harden live web / YouTube / URL research

Run the channel/video/transcript tests above, confirm provenance, caching, bounded enumeration and real passage through the JANUS deliberation fabric. Do not redesign the working bridge unless a concrete failure is observed.

### Priority 2 — finish end-to-end Android attachment validation

Verify pick → authenticated upload → visible chip → send → server grounding/vision/extraction → response provenance. Keep a build assertion that generated Android HTML contains the attachment control and the Java bridge contains the picker callback.

### Priority 3 — Android generated-artifact workflow

Expose JANUS-created research notes, continuity reports, project snapshots and digests with open/download/share actions.

### Priority 4 — Research workspace UI

Separate proven mathematical results, hypotheses, negative results, open questions, evidence and proposed tests. Live URL/transcript research should feed this workspace with provenance.

### Priority 5 — Maintenance/upgrade approval UI

Show the roughly 90-day maintenance proposal and approve/defer/reject state without enabling autonomous self-modification.

### Priority 6 — Background research provenance UI

Readable completed research, sources, transcript/document provenance, suppression reasons and external-compute use.

### Priority 7 — Protocol/capability negotiation

Expose an explicit server/client capability document so JANUS and older clients can truthfully know whether attachments, direct URL ingestion, web search, transcripts, image analysis and generated artifacts are available.

### Priority 8 — Interface theme settings

Add user-selectable interface themes/colour settings in the appropriate client Options UI. Keep this client-facing and separate from server cognition/state.

### Priority 9 — Android release hardening

Reduce patch-script fragility/stale version text, improve narrow-screen diagnostic presentation, and add UI-level regression checks. Prefer hard-coded authoritative product paths where repeated patch composition has proven fragile.

### Priority 10 — Phase 3 release checkpoint

Freeze features, run the full server+Android matrix, document known limits and establish a known-good APK/server protocol baseline.

## Deferred after Phase 3 / economic gates

- Windows/PC parity and Apple/iOS parity remain deferred until explicitly resumed.
- Full autonomous visual candidate render/inspect/revise loops remain revenue/cost gated.
- Future JANUS cores may use images more deeply as a communication/representation medium only after cost controls and product economics justify it.
- Unbounded autonomous YouTube/channel crawling is not part of the baseline; channel/video research stays user-directed or tightly budgeted.

## Working method for next session

Before changing code, review this checkpoint, `JANUS_PHASE3_PRODUCTIZATION.md`, `DEFERRED_FEATURES.md`, the live-web bridge/runtime, `curiosity_search.py`, `interface_chat.py`, the attachment bridge, and the latest GitHub Actions results.

Preserve all later successful commits and fix failures forward rather than reverting working features. Prefer direct authoritative implementation over stacked patch scripts where possible. After implementation commits, use the GitHub Actions progress page to verify the current head rather than judging historical red runs.

Most important current state to remember: **normal Android JANUS Chat has now demonstrated real live web search and indexed YouTube search with returned source URLs. Basic internet capability is working; next work is hardening, transcript/channel verification, provenance, attachments, artifacts, workspace, themes and release hardening.**
