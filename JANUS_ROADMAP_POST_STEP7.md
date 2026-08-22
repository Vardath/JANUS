# JANUS post-Step-7 roadmap

Updated 2026-08-22. Windows/PC and Apple client parity are intentionally skipped for this sequence. Android feature work is not a dedicated roadmap step; server/protocol changes should remain backward-compatible where practical.

## Ordered implementation plan

1. **Project + Question Continuity Ledger** — durable lifecycle for projects, questions, tasks, promises, ideas and research; explicit open/completed/deferred/superseded/contradicted states so JANUS can distinguish unfinished work from history. **IN PROGRESS / foundation committed.**
2. **Continuity integration + contradiction/revision governance** — connect the ledger to Chat, Memory/Context, deliberation and background cognition; detect completion/correction/supersession candidates conservatively; never silently rewrite protected identity/core history.
3. **Federated selective memory synchronization** — formal local/global exchange objects, provenance, conflict detection, merge/supersession rules, bounded remote summaries and no whole-state overwrite.
4. **Unified cost/accounting governor** — per-profile/per-capability usage ledger and configurable daily/monthly budgets for chat escalation, curiosity, background review/synthesis, vision and image generation; graceful throttling before limits.
5. **Maintenance/upgrade request system** — approximately quarterly stack/security/model/dependency review that creates a proposal/report for the user; no autonomous protected-code modification. Email/report delivery can be layered on available account notification infrastructure.
6. **Richer proactive thread continuity** — Messages can refer back to the originating question/project/deliberation, distinguish notification from continuation, and avoid treating routine background activity as a new conversation.
7. **Outbound working artifacts** — server-side JANUS-generated research notes/reports/exports as account-bound files, building on authenticated file storage; avoid client-specific parity work in this sequence.
8. **Visual explanation decision layer** — decide when an explanatory image/diagram materially improves a user answer; use existing bounded Stage-1 image generation and caching rather than autonomous render loops.
9. **Revenue-gated multi-core visual deliberation scaffolding** — concept/critique/selection records and hard budgets, with actual autonomous background rendering remaining disabled until explicitly enabled economically.
10. **Research-question workspace for the JANUS mathematical/physical programme** — seed durable audited/open/negative-result questions from project memory so scientific work can accumulate evidence and falsifications without confusing hypotheses with established results.
11. **Reliability/security/soak audit** — cross-account isolation, persistence/migration, background repetition, cost bounds, crash recovery, schema upgrades and end-to-end server deployment checks.

## Step 1 foundation

`continuity_ledger.py` introduces account/profile-scoped SQLite persistence with two tables: durable continuity items and append-only lifecycle events. Supported item kinds are project, question, task, promise, idea and research. Explicit lifecycle states include proposed, approved, active, investigating, testing, blocked, provisional, completed, resolved, deferred, superseded, contradicted, reopened and cancelled.

The ledger supports creation, revision, state transitions, parent relationships, explicit supersession, priority/tags, event history, open-item listing and a compact `continuity_context()` grounding block for later Memory/Context/background integration. Supersession marks the older item non-current instead of deleting history. Terminal items disappear from the default open context but remain auditable.

`tests/test_continuity_ledger.py` covers question lifecycle, supersession/current-state semantics and profile isolation.

The next part of Step 1 is integration into the active server/runtime and CI; that belongs at the boundary between roadmap items 1 and 2 and should be done without rewriting the reconstructed historical base server unless necessary.
