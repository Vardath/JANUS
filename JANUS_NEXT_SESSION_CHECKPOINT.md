# JANUS next-session checkpoint — 2026-08-23

This file is the authoritative handoff for the next implementation session.

## Current baseline

Phase 2 stabilization is complete in implementation and has a dedicated release-checkpoint workflow. The current Android baseline is v0.69. Windows/PC and Apple/iOS work remains intentionally deferred.

The architecture remains the experimental functional-metacognition/agency JANUS system with the established 7 specialist → 2 hemisphere → Consensus → Interface topology. Do not reinterpret this as a claim of phenomenal consciousness.

Preserve these invariants:
- authenticated account/profile ownership; never trust a client-selected username for private state;
- server and local-device activity are distinct and must be reported separately;
- local/global synchronization is selective and provenance-preserving, never a whole-state overwrite;
- protected identity/core state cannot be overwritten by ordinary conversation/sync state;
- memory retrieval should recover relevant older conversation, prioritize corrections, consolidate duplicates and retain continuity cues such as “think about this”, “ponder”, “mull it over”, “remember this”, and “come back to this”;
- background research is bounded by usefulness/repetition gates and cost controls;
- provider failures degrade gracefully and failed provider calls do not consume estimated-success budget;
- foreground Chat should remain available when optional background budgets are exhausted;
- image generation is user-requested/foreground and bounded; uncontrolled autonomous/background rendering remains disabled;
- maintenance may propose upgrades/reviews but JANUS must not self-modify without owner approval.

## Phase 2 work now present

The repository contains the completed stabilization work: route/security inventory and profile-boundary hardening; persistence/migration matrix and schema preflight; background usefulness audit; memory-quality retrieval; server/local synchronization soak; cost/failure degradation handling; owner-facing observability; Android System Status UI; and the Phase 2 release-checkpoint workflow.

Owner observability should translate telemetry into useful English and distinguish Healthy / Reduced capability / Needs attention. Android v0.69 exposes this under Options → System status.

## Latest live verification

A live Android system-check conversation was reviewed after the v0.69 work. JANUS produced a structured diagnostic covering core topology/operational state, processing and communication, persistence and memory, safety/boundaries, novelty/self-assessment, routing, and internal/antipodal state. The response appeared to be grounded in actual runtime/system terminology rather than a generic reassurance. Functionally the system looked operational and coherent; the remaining weakness was presentation density on a narrow phone screen. Future diagnostic UI should prefer a concise Healthy / Reduced capability / Needs attention summary with expandable detail rather than one very long chat response.

## Attachment regression and restoration

The earlier Android Chat attachment feature was found to have regressed from the authoritative build path even though the implementation itself still existed. The retained `tools/patch_android_file_attachments.py` provides the Chat `+` button, native Android picker, authenticated upload, visible attachment chips, a four-attachment-per-turn limit, attachment removal, and passing uploaded attachment IDs into Chat.

Root cause: the consolidated v0.69 Android workflow had stopped applying the retained attachment patch and only applied the consolidated runtime patch. This was fixed forward in commit `b858f7e` by changing the authoritative Android build order to:

1. `python tools/patch_android_file_attachments.py`
2. `python tools/patch_android_runtime_cores_v068.py`

Do not revert later Android/core/sync/Observe/System Status work to restore attachments. The intended baseline is the current consolidated client plus restored attachment functionality.

A later live screenshot confirmed that the `+` attachment button is visibly restored beside the Chat composer. Treat the UI restoration portion as validated; still retain end-to-end attachment upload/grounding regression coverage so it cannot disappear again.

## Newly observed research/browser gap

A live conversation exposed an important mismatch between JANUS's implemented research fabric and what the Interface believes it can do. When asked whether it could read YouTube transcripts, JANUS replied that it could only analyse transcript text supplied manually and could not automatically open a YouTube channel, enumerate videos, or retrieve transcript material.

Repository review shows that `curiosity_search.py` already gives the 11-core research fabric bounded OpenAI model consultation and live web search, including foreground web escalation for requests containing terms such as search, latest, current, internet, web, research, source, evidence, and verify. Therefore the problem is not that JANUS has no internet research capability at all. The gap is a missing or unexposed **URL/media ingestion layer** and inaccurate capability self-reporting.

Tomorrow, fix this forward rather than teaching JANUS to tell users to manually copy everything it could reasonably retrieve itself.

Required behavior for URL/video research:
1. A user can paste a normal web URL into Chat and JANUS should attempt to retrieve/read the relevant public content using its existing bounded research path.
2. A user can paste a YouTube video URL and JANUS should attempt to obtain available transcript/caption text or a reliable indexed transcript representation when permitted/available, then ground its answer in that material.
3. For a YouTube channel URL or request such as “review this channel,” JANUS should be able to discover/enumerate a bounded set of relevant/recent videos, then inspect available transcripts selectively rather than claiming channel access is categorically impossible.
4. Do not fabricate transcripts. If captions/transcript text are unavailable or blocked, say exactly that and fall back to title/description/search-result evidence.
5. Keep source URL, video title, retrieval time, transcript availability, and provenance with any stored research note.
6. Cache fetched transcript/text by canonical URL/content identity so repeated analysis does not repeatedly spend model/web budget.
7. Respect background/foreground cost governance. Foreground user-requested URL research gets priority; autonomous channel crawling must remain bounded and off by default unless explicitly enabled.
8. Route acquired transcript/document text through the same Evidence/Logic/Counterpoint/Context/Memory/Novelty fabric rather than letting Interface answer from an unexamined scrape.
9. Teach Interface capability reporting to distinguish: web search available; direct URL ingestion available; transcript available/unavailable for this particular video; channel enumeration supported within bounded limits. Do not make generic claims that the environment cannot access the web when the research bridge is enabled.
10. Add regression tests for a successful URL research path, unavailable transcript fallback, no-fabrication behavior, caching, provenance, account isolation, and provider failure degradation.

## Phase 3 status and revised next-session order

Phase 3 is Android/server productization. Step 1 is complete: the capability/deferred registry was reconciled so already-built server capabilities are no longer incorrectly listed as future work.

The Android attachment control has now been visibly restored. The schedule is revised because the live transcript conversation exposed a more important capability/integration hole than the previously planned artifact UI work.

### Tomorrow — revised implementation order

**Priority 1 — URL / YouTube / transcript research integration and truthful capability reporting.**
Implement the behavior specified above using the existing curiosity/web research fabric wherever possible. Prefer a small ingestion/provenance bridge over a second independent research system.

**Priority 2 — finish end-to-end Android attachment validation.**
Verify pick → authenticated upload → visible chip → send → server grounding/vision/extraction → response provenance. Add a build assertion that generated Android HTML contains the attachment control and that the Java bridge contains the picker callback.

**Priority 3 — Android generated-artifact workflow.**
Expose JANUS-created research notes, continuity reports, project snapshots and digests with open/download/share actions.

**Priority 4 — Research workspace UI.**
Separate proven mathematical results, hypotheses, negative results, open questions, evidence and proposed tests. URL/transcript research gathered in Priority 1 should be able to feed this workspace with provenance.

**Priority 5 — Maintenance/upgrade approval UI.**
Show the roughly 90-day maintenance proposal and approve/defer/reject state without enabling autonomous self-modification.

**Priority 6 — Background research provenance UI.**
Readable completed research, sources, transcript/document provenance, suppression reasons and external-compute use.

**Priority 7 — Protocol/capability negotiation.**
Expose an explicit server/client capability document so JANUS and older clients can truthfully know whether attachments, direct URL ingestion, web search, transcripts, image analysis and generated artifacts are available.

**Priority 8 — Android release hardening.**
Reduce patch-script fragility/stale version text, improve narrow-screen diagnostic presentation, and add UI-level regression checks.

**Priority 9 — Phase 3 release checkpoint.**
Freeze features, run the full server+Android matrix, document limits and establish a known-good APK/server protocol baseline.

## Deferred after Phase 3 / economic gates

- Windows/PC parity and Apple/iOS parity remain deferred until explicitly resumed.
- Full autonomous visual candidate render/inspect/revise loops remain revenue/cost gated. The existing visual-deliberation scaffolding may reason about concepts without rendering.
- Future JANUS cores may use images more deeply as a communication/representation medium only after cost controls and product economics justify it.
- Unbounded autonomous YouTube/channel crawling is not part of the baseline; channel/video research should remain user-directed or tightly budgeted.

## Working method for next session

Before changing code, review this checkpoint, `JANUS_PHASE3_PRODUCTIZATION.md`, `DEFERRED_FEATURES.md`, `curiosity_search.py`, the attachment bridge, and the latest GitHub Actions results. Preserve all later commits and fix failures forward rather than reverting successful features. Keep showing the GitHub Actions progress page after implementation commits when useful.
