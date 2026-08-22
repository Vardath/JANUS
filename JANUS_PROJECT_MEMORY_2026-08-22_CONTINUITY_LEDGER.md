# JANUS Step 1 Continuity Ledger Checkpoint — 2026-08-22

This supplement follows `JANUS_PROJECT_MEMORY_2026-08-22_STEP7_BACKGROUND_COGNITION.md` and the post-Step-7 roadmap in `JANUS_ROADMAP_POST_STEP7.md`.

## Step 1 complete: Project + Question Continuity Ledger

JANUS now has explicit durable work-state objects separate from transient conversation memory. The goal is to stop relying on loose recall to determine whether something is still open, completed, deferred, contradicted or superseded.

### Durable object kinds
- project
- question
- task
- promise
- idea
- research

### Lifecycle states
- proposed
- approved
- active
- investigating
- testing
- blocked
- provisional
- completed
- resolved
- deferred
- superseded
- contradicted
- reopened
- cancelled

`continuity_ledger.py` stores account/profile-scoped items and append-only lifecycle events. It preserves superseded/terminal history while excluding terminal work from the normal open-context view. It supports parent/supersession relationships, priorities, tags, revision events, explicit transitions and duplicate-safe open-item reaffirmation.

### Active Chat integration

`interface_chat.py` now supplies the open continuity ledger as primary grounding alongside whole-history memory and the 11-core foreground deliberation. The Interface contract explicitly uses the ledger to distinguish unfinished work from completed/superseded history and must not invent state changes merely from conversational implication.

### Deliberation integration

`continuity_api.py` wraps the existing deliberation-aware chat route. When the user explicitly asks JANUS to keep thinking/ponder/mull something across later cycles, the resulting durable deliberation is also represented as an investigating continuity question. Reaffirming the same question does not create repeated open ledger entries.

### Server API

New endpoints:
- `GET /desktop/continuity`
- `POST /desktop/continuity`
- `POST /desktop/continuity/{item_id}/state`
- `GET /desktop/continuity/{item_id}/events`

These are server/protocol capabilities; no dedicated Windows/Apple client work is part of this roadmap sequence.

### Regression/CI

`tests/test_continuity_ledger.py` covers lifecycle transitions, supersession/current-state behavior and profile isolation. The main cognition CI now compiles the continuity modules and runs the ledger tests alongside epistemic regulation, autonomous-message quality and longitudinal background-cognition tests.

## Next step

**Step 2: continuity contradiction/revision governance.**

JANUS needs a conservative mechanism to propose rather than silently apply lifecycle changes when conversation indicates that a plan has been completed, a claim corrected, a question contradicted, or a newer plan supersedes an older one. User statements and explicit verified execution should have higher authority than assistant/model paraphrases. Protected identity/core history must remain outside this mechanism.
