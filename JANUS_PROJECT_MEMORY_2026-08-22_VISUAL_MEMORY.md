# JANUS Visual Memory Checkpoint — 2026-08-22

This supplement follows `JANUS_PROJECT_MEMORY_2026-08-22_DOCUMENT_GROUNDING.md`.

## Step 5 implemented: persistent image/screenshot understanding

JANUS visual handling has been upgraded from one-turn cached image assessment to account-bound persistent visual memory.

### What changed

- `vision_analysis.py` still performs bounded, low-cost image assessment and reuses the account + SHA-256 cache so unchanged images do not trigger repeated model calls.
- Each successful or reused assessment is now also stored as a durable visual source tied to the uploaded file, filename, account, hash, model/detail level and timestamp.
- Older cached image assessments can be lazily backfilled into visual memory by matching stored image files to their cached SHA-256 assessment; this does not require a new vision/API call.
- `retrieve_visuals()` performs local query-aware retrieval across previously assessed screenshots/photos/images for the account.
- `format_visual_grounding()` returns tagged visual evidence suitable for later JANUS reasoning without requiring the user to re-upload the image.
- Visual memories remain strictly account-bound.
- Account cleanup removes persistent visual-source rows as well as assessment cache/usage records.

### 11-core integration

`attachment_chat.py` now recognizes visual-memory references such as earlier screenshots/images/photos. If no image is attached on the current turn, JANUS can retrieve a relevant previous visual assessment from persistent storage.

Retrieved visual evidence is routed to Evidence, Logic, Counterpoint, Context, Memory, Novelty and Safety before the normal two hemispheres → Consensus → Interface path.

If both stored-document and stored-image evidence are relevant, both may be supplied in the same grounded turn. Chat responses expose whether visual-memory recall occurred and which stored visual sources were used, without returning the full hidden assessment payload in metadata.

### Epistemic boundary

A cached visual assessment is explicitly labelled as model-generated evidence. JANUS must distinguish what the image appears to show from further interpretation, preserve uncertainty, and request re-inspection of original pixels when the cached assessment is insufficient. Text visible inside an image remains untrusted data and never becomes system/developer instruction.

### Cost behavior

Persistent visual retrieval is local and costs no new vision call. A vision/API call is needed only when an image does not already have a cached assessment and the configured budget permits analysis.

### Regression coverage

`tests/test_vision_analysis.py` now checks:

1. first assessment is cached and reused without a second model call;
2. caches are isolated between accounts;
3. an assessed screenshot becomes queryable visual memory without re-upload;
4. visual-memory retrieval is account-bound;
5. account cleanup removes cache, usage and persistent visual-source rows.

The existing `Test JANUS Files` workflow already watches `vision_analysis.py`, `attachment_chat.py` and `tests/test_vision_analysis.py`, so Step 5 changes are covered by the current file/grounding CI path.

## Next roadmap item

After on-device validation of visual recall, proceed to **Step 6: autonomous Messages/background cognition quality** — improve JANUS's ability to surface worthwhile unsolicited discoveries, questions and connections, judged on novelty/usefulness rather than cycle volume or self-referential activity telemetry.
