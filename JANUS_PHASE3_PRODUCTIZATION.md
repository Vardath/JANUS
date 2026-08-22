# JANUS Phase 3 — Android/server productization

Phase 2 established the stabilization baseline. Phase 3 turns the capabilities already implemented on the server into coherent, discoverable Android product workflows without reopening the deferred Windows or Apple clients.

## Scope boundary

- Android + server only for this phase.
- Do not redesign the 7→2→1→1 core architecture.
- Preserve authenticated account ownership, selective sync, conflict provenance and no-whole-state-overwrite guarantees.
- Prefer wiring existing capabilities into the product over inventing new subsystems.
- Keep autonomous paid work bounded and background image rendering disabled.

## Ordered plan

1. **Reconcile capability/deferred registry** — remove stale roadmap entries for server features already completed and explicitly identify the client/product gaps that remain. **IMPLEMENTED.**
2. **Android attachment workflow** — add file/image picker, upload progress, account-bound attachment list, deletion, and attachment references in Chat. Reuse the existing server attachment/document-grounding/vision stack rather than creating a second upload path.
3. **Android generated-artifact workflow** — expose JANUS-created research notes, continuity reports, project snapshots and digests in the app with download/open/share actions.
4. **Research workspace UI** — expose hypotheses, proven mathematical results, negative results, open questions, evidence and proposed tests as distinct readable categories in Android.
5. **Maintenance/upgrade approval UI** — surface JANUS's 90-day maintenance proposal, owner notification state and approve/defer/reject workflow without permitting self-modification.
6. **Background research provenance UI** — show useful completed autonomous research, source provenance, suppression reasons and external-compute usage in readable form rather than raw telemetry.
7. **Protocol/capability negotiation** — publish an explicit server/client capability document so old Android clients can degrade cleanly when the server gains new endpoints and the server can distinguish missing client capabilities from failures.
8. **Android release hardening** — consolidate patch scripts further, remove stale version text/legacy injection assumptions, and add UI-level regression checks for the major Android screens.
9. **Phase 3 release checkpoint** — freeze feature additions, run the full server + Android matrix, document known limits and publish a known-good APK/server protocol baseline.

## Already implemented and therefore not deferred anymore

The server already has authenticated file storage, document grounding, selective vision escalation, one-shot foreground image generation, bounded visual-explanation decisions, multi-core visual-deliberation scaffolding, outbound working artifacts, owner observability, research workspace, maintenance-review proposals, cost governance, memory-quality retrieval and selective federated synchronization.

The remaining work is largely product integration and evidence that these pieces work together cleanly from Android.
