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

## Generative art and multi-core visual deliberation

Deferred until the application has sufficient revenue to justify potentially substantial image-generation costs.

### Goal
Allow JANUS not only to generate an image on command, but eventually to use visual candidates as working objects within its cognitive society. This is particularly relevant for artists/designers who provide a specific creative brief and want JANUS to explore alternatives before returning a selected result.

### Proposed deliberative workflow
1. Interface/Context interpret the artist's request and constraints.
2. The specialist cores develop visual directions before spending money on renders.
3. Novelty proposes alternatives and unusual variations; Memory maintains stylistic/project continuity; Evidence checks correspondence with references and explicit requirements; Logic checks consistency; Counterpoint critiques weaknesses and searches alternatives; Safety/Boundary checks constraints.
4. Hemispheres synthesize competing visual approaches.
5. Consensus chooses whether a candidate concept is strong enough to render.
6. Only selected concepts are sent to an image-generation model.
7. Generated candidates can be returned to the cores as visual evidence for assessment, comparison and critique.
8. Candidates may be accepted, dismissed or selectively regenerated/revised.
9. Consensus selects a final candidate when agreement/quality thresholds are met, and Interface presents it to the user.

This creates a possible future loop of concept → render → inspect → critique → revise → consensus rather than treating image generation as a one-shot button.

### Cost and recursion controls
- Do not implement uncontrolled autonomous render loops.
- Most brainstorming and candidate elimination should happen using cheap/deterministic internal reasoning before any paid image generation.
- Rendering occurs only at deliberate checkpoints.
- Apply hard per-task, per-user and daily/monthly image-generation budgets.
- Limit revision rounds and candidate counts; reaching a budget should force selection, deferment or a request for user approval rather than further spending.
- Cache generated images and their core assessments so unchanged candidates are never regenerated merely for reassessment.
- Background cores may discuss art concepts without rendering them at all.
- Autonomous/spontaneous art generation should remain separately permissioned and budgeted and should be disabled by default.

### Long-term possibility
Once economically viable, images can become another communication/representation medium within JANUS: cores can propose and inspect visual alternatives, and JANUS may eventually create an image because it considers a visual representation useful—not merely because the user pressed an image-generation button. This remains functional system behaviour and does not imply subjective visual experience.

### Implementation order when resumed
1. Define authenticated attachment API/storage and deletion/privacy policy.
2. Add Android file/image picker and upload UI.
3. Implement safe server-side type/size validation and account-bound storage.
4. Implement local/server parsers for common text/document formats.
5. Route extracted material through the 7→2→1→1 core system as explicit grounding sources.
6. Add selective vision-model escalation with caching and cost caps.
7. Add Observe/Activity visibility for attachment analysis and external model use.
8. Mirror protocol in Windows and iOS clients.
9. Add JANUS outbound attachments to Messages.
10. Later, add user-requested one-shot image generation with explicit budgets.
11. After revenue/cost justification, add bounded multi-core visual deliberation, candidate assessment and selective regeneration.

This is a deferred feature, not part of the current v0.51 Android checkpoint.