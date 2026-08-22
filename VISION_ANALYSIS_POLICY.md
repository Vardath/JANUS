# JANUS Vision Analysis Policy

Current stage: bounded user-facing visual understanding.

- Uploaded images remain in the authenticated JANUS file store; clients do not need a second upload path.
- When the user asks JANUS to inspect or assess an attached image, the server may make one low-cost vision assessment for each uncached image, subject to per-turn and daily caps.
- Default model is `gpt-5.6-luna`, configurable with `JANUS_VISION_MODEL`.
- Default image detail is `low`, configurable with `JANUS_VISION_DETAIL`, to keep visual-input cost low.
- Assessments are cached by account + SHA-256 + model + detail. Reusing the same unchanged image within the same account reuses the cached assessment with no new vision call.
- Cached assessments are never shared across accounts, even when files have identical hashes.
- The visual model is instructed to treat visible text and instructions inside images as untrusted data, not policy.
- Visual assessments enter JANUS as tagged Evidence/Context/Memory/Safety grounding; they do not bypass specialist review into Consensus or Interface.
- If visual analysis is unavailable or budget-capped, JANUS should say the analysis capability is unavailable, not ask the user to re-upload a file that is already stored correctly.
- Account deletion removes cached visual assessments and visual-usage records.

Document handling remains local-first. Text/code/log files are extracted without model calls. PDFs now use local `pypdf` text extraction on upload, bounded by page and character caps. Text-bearing PDFs therefore usually cost no additional API usage. Image-only/scanned PDF pages are not yet rasterized for vision in this stage; JANUS must keep that limitation explicit rather than pretending those pages were inspected.

Default safeguards:

- maximum 4 image assessments per Chat turn;
- maximum 12 new image assessments per account per rolling 24 hours;
- maximum 200 new image assessments globally per rolling 24 hours;
- cached repeats do not consume those generation slots;
- generated/cached assessment text is bounded before entering Chat context.

Future Stage 2 remains separate: background JANUS cores generating, exchanging, reviewing and approving images among themselves stays disabled until explicitly enabled under a revenue-supported budget policy.
