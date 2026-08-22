# JANUS Document Grounding Checkpoint — 2026-08-22

This supplement follows `JANUS_PROJECT_MEMORY_2026-08-22.md`.

## Step 4 implemented: richer document/file grounding

The earlier attachment path could store files and locally extract text/PDF content, but Chat generally received only a bounded prefix. That was insufficient for long reports, papers, logs, code, and documents where the relevant material appeared later.

The new `document_grounding.py` layer provides persistent, account-bound, zero-paid-API chunk indexing and query-aware retrieval:

- extracted document text is divided into overlapping chunks;
- PDF page markers are preserved so retrieved claims retain page provenance where available;
- chunks are persisted in SQLite and remain account-bound;
- a user question retrieves the most relevant chunks rather than blindly supplying the beginning of a file;
- neighbouring chunks are added around strong matches to preserve local context;
- vague attached-file requests receive a representative beginning/middle/end spread instead of an empty result;
- older uploaded text-bearing files are lazily backfilled into the chunk index;
- later questions such as “what did the report I sent say about X?” can retrieve relevant passages from the account document library without requiring the user to re-upload the file;
- document text is explicitly tagged as user-supplied/untrusted evidence, never as system instructions;
- filename plus page/chunk provenance is supplied to the JANUS society;
- Evidence, Logic, Counterpoint, Context, Memory, Novelty and Safety all receive relevant document grounding before the normal hemisphere → Consensus → Interface path.

## Expanded local extraction

`attachment_api.py` now locally extracts common office/document types in addition to the previous text/code/PDF path:

- DOCX;
- PPTX;
- XLSX;
- ODT;
- RTF;
- existing text/code/CSV/JSON/etc.;
- text-bearing PDFs.

Office ZIP extraction has a bounded uncompressed-size guard. PDF and office extraction retain configured character/page limits. Images remain on the separate visual-analysis path.

New uploads with extracted text are indexed immediately. Older uploads are indexed lazily when referenced. Deleting a file also removes its document index.

## Compatibility and safety

The existing attachment grounding helper keeps its prior `(items, grounding)` interface so established tests/callers remain compatible. The wrapper now adapts to either request-aware or payload-only Chat endpoints.

No embeddings or paid model calls are required for indexing/retrieval. A model may still be used by normal JANUS Chat after the relevant passages have been selected locally.

Regression tests were added for:

1. finding a relevant passage late in a long document rather than only reading the prefix;
2. later document-library recall without reattachment;
3. account isolation of indexed document content.

## Next roadmap item

After deploying and testing document grounding on-device, proceed to **Step 5: image/screenshot understanding**. Existing `vision_analysis.py` already supplies a bounded cached image assessment path, so Step 5 should focus on making visual material a first-class, persistent, queryable source for the 11-core society rather than merely a one-turn attachment observation.
