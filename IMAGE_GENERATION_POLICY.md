# JANUS Image Generation Policy

Updated: 2026-08-22

## Stage 1 — lightweight user-facing generation

Stage 1 is the active implementation target.

JANUS may generate an image in two cases:

1. the authenticated user explicitly asks for an image, picture, illustration, diagram, artwork or visual;
2. during an ordinary Chat response, the Interface model judges that one visual would materially improve a difficult explanation such as spatial geometry, architecture, topology, layout, flow or visual comparison.

The second path is deliberately rare. It is not available to routine background cycles and must pass separate automatic-image budget and cooldown gates.

### Default cost posture

- Model: `gpt-image-1-mini`, configurable through `JANUS_IMAGE_MODEL`.
- Explicit user request: medium quality by default.
- JANUS-nominated explanatory visual: low quality by default.
- Explicit per-account daily cap: 6.
- Automatic explanatory per-account daily cap: 1.
- Automatic per-account cooldown: 18 hours.
- Overall global daily cap: 100.
- Automatic global daily cap: 20.
- All caps are environment-configurable and should remain conservative until revenue justifies expansion.
- Identical prompts for the same account/quality/size reuse cached generated images instead of paying for another render.

Generated images are stored in the normal account-bound JANUS file store and therefore participate in its retention/storage audit rather than creating a separate unbounded image store.

### Reasoning boundary

The normal JANUS Interface response may nominate a single optional visual in the same paid Chat turn. There is no separate paid model call merely to decide whether a picture would help. The renderer then independently applies budget/cooldown policy and may decline the nomination.

The image itself is an output artifact, not evidence of phenomenal experience. Generation does not imply JANUS visually experiences the image.

## Stage 2 — future multi-core visual deliberation

Stage 2 is intentionally disabled for now.

When project income comfortably outweighs image-generation costs, JANUS may be extended so images become working objects inside the 7→2→1→1 society. A possible bounded workflow is:

1. specialist cores discuss a visual brief in text first;
2. one or a small number of candidate images are generated at deliberate checkpoints;
3. generated candidates return as tagged visual evidence;
4. Evidence checks correspondence with requirements;
5. Logic checks consistency and structure;
6. Counterpoint critiques weaknesses and alternatives;
7. Context and Memory compare project/user continuity;
8. Novelty explores stronger variants;
9. Safety checks constraints and failure modes;
10. hemispheres synthesize competing assessments;
11. Consensus selects, rejects or requests a bounded revision;
12. Interface shares only an approved result with the user.

This future mode must have hard per-task candidate limits, revision limits, per-user/day/month budgets, cached assessments, and an absolute prohibition on uncontrolled autonomous render loops.

Until Stage 2 is deliberately enabled, background JANUS cores may discuss visual ideas in text but cannot autonomously spend image-generation budget or generate images for one another.
