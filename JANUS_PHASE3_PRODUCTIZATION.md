# JANUS Phase 3 — Android/server productization

Phase 2 established the stabilization baseline. Phase 3 turns implemented server capabilities into coherent Android workflows.

## Scope boundary
- Android + server only.
- Preserve 7→2→1→1 architecture, authenticated ownership, selective sync/provenance, and no whole-state overwrite.
- Keep autonomous paid work bounded and background image rendering disabled.

## Ordered plan
1. Capability/deferred registry — **IMPLEMENTED.**
2. URL / YouTube / transcript research integration — **IMPLEMENTED 2026-08-23; deployment/regression validation pending.** Direct public URL text ingestion, per-video transcript attempts, provenance, profile-isolated caching, no-fabrication fallback and truthful capability reporting.
3. Android attachment workflow — UI restored; end-to-end regression validation remains.
4. Android generated-artifact workflow.
5. Research workspace UI.
6. Maintenance/upgrade approval UI.
7. Background research provenance UI.
8. Protocol/capability negotiation.
9. Android release hardening.
10. Phase 3 release checkpoint.

## URL/media boundary
Foreground pasted URLs are fetched directly where public text is available. YouTube video URLs attempt captions/transcripts and retain an explicit unavailable state rather than fabricating text. Retrieved material is injected into the existing multi-core research fabric. Cache keys are profile + canonical URL. Channel-wide autonomous crawling remains disabled; bounded channel discovery continues through the existing web-search fabric.
