# JANUS Phase 3 — Android/server productization

Phase 2 established the stabilization baseline. Phase 3 turns implemented server capabilities into coherent Android workflows.

## Scope boundary
- Android + server only.
- Preserve 7→2→1→1 architecture, authenticated ownership, selective sync/provenance, and no whole-state overwrite.
- Keep autonomous paid work bounded and background image rendering disabled.

## Ordered plan
1. Capability/deferred registry — **IMPLEMENTED.**
2. URL / YouTube / transcript research integration — **IMPLEMENTED 2026-08-23; deployment/regression validation pending.** Direct public URL text ingestion, per-video transcript attempts, provenance, profile-isolated caching, no-fabrication fallback and truthful capability reporting.
3. Android attachment workflow — **IMPLEMENTED; regression/productization CI added, live end-to-end validation pending.** Native picker, account-bound upload, attachment chips, four-file turn limit and specialist grounding are preserved in the authoritative build chain.
4. Android generated-artifact workflow — **IMPLEMENTED IN CLIENT BUILD PATH; CI/live validation pending.** Android Options now exposes account-bound continuity reports and research digests, lists existing JANUS artifacts, opens provenance/details and can attach generated artifact files back into Chat for grounded discussion. Native OS export/share/download remains a later hardening subtask.
5. Research workspace UI.
6. Maintenance/upgrade approval UI.
7. Background research provenance UI.
8. Protocol/capability negotiation.
9. Android release/UI hardening — includes native artifact export/share/download, patch-chain reduction, UI regression assertions, stale-version cleanup, and configurable interface themes (system/light/dark plus accent/theme colours with readable contrast).
10. Phase 3 release checkpoint.

## URL/media boundary
Foreground pasted URLs are fetched directly where public text is available. YouTube video URLs attempt captions/transcripts and retain an explicit unavailable state rather than fabricating text. Retrieved material is injected into the existing multi-core research fabric. Cache keys are profile + canonical URL. Channel-wide autonomous crawling remains disabled; bounded channel discovery continues through the existing web-search fabric.

## Interface theme backlog
Theme controls belong to the client/productization layer, not JANUS cognition. Preserve accessibility/readable contrast. Planned controls: system/light/dark appearance, preset accent palettes, optional custom accent/surface colours, and subtle optional role colours for specialist/hemisphere/consensus views without making the interface noisy.
