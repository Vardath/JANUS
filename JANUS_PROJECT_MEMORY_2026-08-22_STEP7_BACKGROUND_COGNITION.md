# JANUS Step 7 Background Cognition Quality Checkpoint — 2026-08-22

This supplement follows `JANUS_PROJECT_MEMORY_2026-08-22_STEP6_AUTONOMOUS_MESSAGES.md`.

## Step 7 implemented: longitudinal background cognition quality

Step 6 made individual autonomous Messages selective. Step 7 adds a longer-horizon layer so JANUS can judge whether background material is actually new relative to its own recent background work and can occasionally connect distinct research findings rather than treating every search/reflection as an isolated item.

### Repeated-source suppression

`autonomous_messages.py` now compares each new background source item against recent raw background material, including items that were previously kept silent. Highly similar material is rejected before a paid message-review call. This prevents repeated research/reflection loops from consuming API budget merely because none of the earlier copies surfaced to the user.

### Cross-research synthesis

New `background_cognition.py` maintains a bounded longitudinal research portfolio over completed curiosity searches. It can select two sufficiently distinct, previously unused research results and, at most rarely, ask the configured background model whether there is a genuine useful connection, contradiction, shared mechanism, boundary condition, prediction, or test between them.

Connections are not forced. The model can decline. A useful synthesis is persisted as `background_synthesis` working memory and as a background source event. It does not automatically notify the user: it must still survive the normal Step 6 autonomous-message quality gate on a later scan.

Defaults are deliberately conservative:
- at most 1 synthesis attempt per profile per day;
- minimum 6 hours between synthesis attempts;
- ordinary autonomous Messages remain capped separately.

Environment controls:
- `JANUS_BACKGROUND_SYNTHESIS_DAILY_CAP` (default 1)
- `JANUS_BACKGROUND_SYNTHESIS_MIN_GAP_SECONDS` (default 21600)

### Longitudinal diagnostics

`/desktop/message-quality?username=...` now includes a `background_portfolio` summary showing recent completed research count, distinct recent themes, synthesis attempts/useful syntheses, and the synthesis budget. The same status includes surfaced/reviewed ratio.

### Epistemic boundary

Background syntheses are model-generated interpretations over retrieved research notes, not new empirical evidence. They remain working-memory material unless independently supported/promoted. A cross-topic analogy is not accepted merely because it sounds coherent.

### Regression coverage

`tests/test_background_cognition.py` checks repeated-query detection, distinct-topic preservation, duplicate-research avoidance in pair selection, and human-subject-matter topic signatures. The curiosity CI now compiles `background_cognition.py` and runs the Step 7 suite alongside the Step 6 and epistemic-regulation tests.

## Expected behavior

Over time JANUS should become less likely to repeatedly reconsider the same background material and more likely to retain genuinely different inputs. Occasionally, two separate research findings may produce a concrete synthesis candidate. Most such material should remain silent; only a useful, non-repetitive result that passes the existing Message gate should interrupt the user.

## Next roadmap

Validate Step 7 over live background operation. Watch for topic diversity, low repetition, useful synthesis quality and reasonable API use. After that, the remaining deferred major capability is richer visual deliberation/background image generation between cores, still subject to cost/usage economics.
