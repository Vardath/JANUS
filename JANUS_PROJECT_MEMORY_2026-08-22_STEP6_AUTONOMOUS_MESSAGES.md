# JANUS Step 6 Autonomous Messages Checkpoint — 2026-08-22

This supplement follows `JANUS_PROJECT_MEMORY_2026-08-22_VISUAL_MEMORY.md`.

## Step 6 implemented: autonomous Messages/background cognition quality

The earlier background systems could generate real activity and research, but user-facing Messages were still vulnerable to self-referential process chatter, raw telemetry, repeated observations, or a disconnect between newer curiosity/hive events and the legacy message promoter.

### New quality layer

`proactive_quality.py` provides a deterministic zero-API gate for autonomous notifications. It scores candidate material for concrete subject matter, usefulness, novelty relative to recent Messages, repetition, and process/telemetry dominance.

Automatic messages are rejected when they are primarily about cycles, routing, Fano/control numbers, integration/process descriptions, or near-duplicates of recent notifications. Explicit user-requested Messages are not filtered by this automatic gate.

### Background source bridge

`autonomous_messages.py` now reviews the modern background sources that actually carry substantive material:

- completed live curiosity/web research;
- paid hive language reflections;
- legacy background reflections.

Candidates first pass a deterministic pre-filter. Only plausible material is sent to the inexpensive background model for a final interrupt-worthiness decision and rewrite. The model is instructed that most candidates should remain silent and that surfaced messages must state what was found/thought and why it matters, rather than merely saying JANUS has been active.

### Rate and repetition control

Autonomous Messages default to a maximum of 3 per profile per day with a 3-hour minimum gap. These are configurable with `JANUS_AUTONOMOUS_MESSAGES_DAILY_CAP` and `JANUS_AUTONOMOUS_MESSAGES_MIN_GAP_SECONDS`.

A persistent `janus_autonomous_message_review` table records reviewed candidates, whether they surfaced, their quality score and the decision reason. `/desktop/message-quality?username=...` exposes operational status for debugging.

### Existing Messages cleanup

The Messages listing now suppresses legacy automatic telemetry-heavy outbox entries while preserving explicit/manual/chat-generated items. This prevents old low-value autonomous entries from dominating the user-facing Messages tab.

### Regression coverage

`tests/test_proactive_quality.py` verifies:

1. telemetry/process chatter is rejected;
2. a concrete discovery/testable connection can pass;
3. near-duplicate autonomous messages are suppressed;
4. explicit chat-requested Messages are never hidden by the automatic filter;
5. legacy autonomous telemetry is hidden.

The curiosity workflow now compiles `autonomous_messages.py` and `proactive_quality.py` and runs the proactive quality regression suite.

## Expected user-facing behavior

JANUS should generally remain quiet unless background work yields something genuinely worth interrupting the user for: a new web discovery, a non-obvious but testable connection, a contradiction, a useful unresolved question, or a concrete next experiment. Activity volume, cycle counts, and self-description are not sufficient reasons to notify.

## Next roadmap item

After validating autonomous Messages in live use, the next planned capability is the previously deferred richer visual deliberation/background image generation between cores, but only when cost/usage economics justify it. Before that, continue normal regression and integration cleanup if live behavior exposes gaps.
