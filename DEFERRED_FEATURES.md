# JANUS Deferred Feature Roadmap

Updated: 2026-08-21

## File sharing, document understanding and image recognition

Deferred for later implementation at the user's request.

### Goal
Give JANUS the ability to receive and reason over user-provided files and images in the same broad way ChatGPT can, while preserving JANUS's local-first, bounded-cost architecture and 7→2→1→1 reasoning topology.

### File sharing
- Android, Windows and iOS clients should eventually support attaching files to Chat and, where useful, Messages.
- Initial formats should include TXT, Markdown, JSON, CSV, source code, logs and PDFs; Office-document support can follow.
- Prefer local parsing/extraction/indexing where practical. Do not automatically send entire files to a paid model.
- Extracted/chunked material should become an explicit grounding source for Evidence, Context, Memory, Logic and other specialists as appropriate.
- Store reusable parsed/extracted representations so the same file is not repeatedly analysed at API cost.
- Large files should be chunked and retrieved selectively rather than injected wholesale into every reasoning pass.
- File access must remain account-bound and respect deletion/privacy controls.

### Image recognition / vision
- Clients should support attaching photographs, screenshots and other supported images.
- Use local metadata/basic preprocessing where useful, then selectively escalate to a vision-capable model when semantic image understanding is required.
- Persist a reusable description/observation record so unchanged images do not need repeated paid analysis.
- Vision results are evidence, not automatic truth. They should pass through the specialist society: e.g. Evidence extracts visible facts, Logic tests interpretation, Counterpoint considers alternatives, Context/Memory relate prior material, Novelty explores testable connections, Safety/Boundary marks uncertainty.
- Screenshots are an important target use case because JANUS should eventually be able to diagnose app/game/build problems from screenshots in the same workflow used for text logs.

### Cost policy
- The upload/attachment plumbing itself should not require AI/API usage.
- Prefer JANUS-owned local/server parsing and indexing over paid hosted retrieval where feasible.
- API costs occur only when semantic model/vision analysis or other paid external processing is actually needed.
- Avoid automatic expensive analysis on every attachment or background cycle. Specialist cores should be able to request escalation when local understanding is insufficient.
- Cache/reuse analysis results and integrate them into JANUS memory to avoid duplicate cost.

### Future outbound files
- JANUS Messages may eventually support JANUS-generated attachments such as reports, research notes, logs, exported memories, documents or images, rather than remaining text-only.

### Implementation order when resumed
1. Define authenticated attachment API/storage and deletion/privacy policy.
2. Add Android file/image picker and upload UI.
3. Implement safe server-side type/size validation and account-bound storage.
4. Implement local/server parsers for common text/document formats.
5. Route extracted material through the 7→2→1→1 core system as explicit grounding sources.
6. Add selective vision-model escalation with caching and cost caps.
7. Add Observe/Activity visibility for attachment analysis and external model use.
8. Mirror protocol in Windows and iOS clients.
9. Add JANUS outbound attachments to Messages later.

This is a deferred feature, not part of the current v0.51 Android checkpoint.