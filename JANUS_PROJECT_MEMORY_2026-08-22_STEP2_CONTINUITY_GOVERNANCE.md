# JANUS Step 2 Continuity Governance Checkpoint — 2026-08-22

Step 1 established a durable project/question ledger. Step 2 adds conservative revision/currentness governance so old conversational memory can remain historically available without being mistaken for current project state.

## Implemented

- Explicit lifecycle language can update tracked continuity items: completed, resolved, deferred, contradicted, cancelled, superseded/replaced and reopened.
- Automatic mutation requires a strong textual match to one tracked item.
- Pronoun-only or otherwise ambiguous lifecycle statements never silently choose an item. They return candidates for clarification.
- Every applied state change is appended to the lifecycle event history; prior content is not deleted.
- Chat applies governance before building continuity/context grounding, so a newly completed or contradicted item immediately stops appearing as open work.
- Chat receives a separate continuity-currentness block. Lifecycle metadata outranks stale conversational references when deciding whether tracked work is current.
- User-authored historical memory is still retained and may be recalled as history; governance changes currentness, not history.
- The 11-core foreground deliberation also sees the revision outcome/currentness data, so Memory/Context/Consensus cannot treat a superseded item as an active commitment simply because an older memory was retrieved.

## Safety/epistemic rule

Do not infer lifecycle changes merely from conversational implication. If the user says something vague like “that is done” and multiple open items exist, JANUS should clarify rather than guess. Protected identity/core history is outside this governance mechanism.

## Regression coverage

`tests/test_continuity_governance.py` checks confident completion, ambiguity refusal, contradicted-history preservation and explicit reopening/audit events. `.github/workflows/test-curiosity.yml` compiles the new module and runs the Step 1+2 continuity suites.

## Next roadmap item

Step 3: federated selective memory synchronization — formal provenance-bearing exchange records, conflict/currentness handling, bounded remote summaries and no whole-state overwrite.
