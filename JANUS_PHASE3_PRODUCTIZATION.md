# JANUS Phase 3 — Android/server productization

Phase 2 established the stabilization baseline. Phase 3 turns the capabilities already implemented on the server into coherent, discoverable Android product workflows without reopening the deferred Windows or Apple clients.

## Scope boundary

- Android + server only for this phase.
- Do not redesign the 7→2→1→1 core architecture.
- Preserve authenticated account ownership, selective sync, conflict provenance and no-whole-state-overwrite guarantees.
- Prefer wiring existing capabilities into the product over inventing new subsystems.
- Keep autonomous paid work bounded and background image rendering disabled.

## Ordered plan

1. **Reconcile capability/deferred registry** — **IMPLEMENTED.**
2. **URL / YouTube / transcript research integration** — direct public URL text ingestion, per-video transcript attempts, provenance, profile-isolated caching, no-fabrication fallback and truthful capability reporting. **IMPLEMENTED 2026-08-23; deployment/regression validation pending.**
3. **Android attachment workflow** — UI restored; end-to-end regression validation remains.
4. **Android generated-artifact workflow** — expose JANUS-created research notes, continuity reports, project snapshots and digests in the app with download/open/share actions.
5. **Research workspace UI** — expose hypotheses, proven mathematical results, negative results, open questions, evidence and proposed tests as distinct readable categories in Android.
6. **Maintenance/upgrade approval UI** — surface JANUS's 90-day maintenance proposal, owner notification state and approve/defer/reject workflow without permitting self-modification.
7. **Background research provenance UI** — show useful completed autonomous research, source provenance, suppression reasons and external-compute usage in readable form rather than raw telemetry.
8. **Protocol/capability negotiation** — publish an explicit server/client capability document so old Android clients can degrade cleanly when the server gains new endpoints.
9. **Android release hardening** — consolidate patch scripts further, remove stale version text/legacy injection assumptions, and add UI-level regression checks.
10. **Phase 3 release checkpoint** — freeze feature additions, run the full server + Android matrix, document known limits and publish a known-good APK/server protocol baseline.

## URL/media implementation boundary

Foreground pasted URLs are fetched directly where public text is available. YouTube video URLs attempt captions/transcripts and retain an explicit unavailable state rather than fabricating text. Retrieved material is injected into the existing multi-core research fabric, not answered from as a separate unexamined subsystem. Cache keys are profile + canonical URL. Channel-wide autonomous crawling remains disabled; bounded channel discovery can continue through the existing web-search fabric.

## Already implemented and therefore not deferred anymore

The server already has authenticated file storage, document grounding, selective vision escalation, one-shot foreground image generation, bounded visual-explanation decisions, multi-core visual-deliberation scaffolding, outbound working artifacts, owner observability, research workspace, maintenance-review proposals, cost governance, memory-quality retrieval and selective federated synchronization.
