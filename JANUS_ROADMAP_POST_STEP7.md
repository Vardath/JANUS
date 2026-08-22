# JANUS post-Step-7 roadmap

Updated 2026-08-22. Windows/PC and Apple client parity are intentionally skipped for this sequence. Android feature work is not a dedicated roadmap step; server/protocol changes should remain backward-compatible where practical.

## Ordered implementation plan

1. **Project + Question Continuity Ledger** — durable lifecycle for projects, questions, tasks, promises, ideas and research; explicit open/completed/deferred/superseded/contradicted states so JANUS can distinguish unfinished work from history. **COMPLETE.**
2. **Continuity integration + contradiction/revision governance** — connect the ledger to Chat, Memory/Context, deliberation and background cognition; detect completion/correction/supersession candidates conservatively; never silently rewrite protected identity/core history. **COMPLETE.**
3. **Federated selective memory synchronization** — formal local/global exchange objects, provenance, conflict detection, merge/supersession rules, bounded remote summaries and no whole-state overwrite. **COMPLETE.**
4. **Unified cost/accounting governor** — per-profile/per-capability usage ledger and configurable daily/monthly budgets for chat escalation, curiosity, background review/synthesis, vision and image generation; graceful throttling before limits. **COMPLETE.**
5. **Maintenance/upgrade request system** — approximately quarterly stack/security/model/dependency review that creates a proposal/report for the user; no autonomous protected-code modification. **IMPLEMENTED.**
6. **Richer proactive thread continuity** — Messages can refer back to the originating question/project/deliberation, distinguish notification from continuation, and avoid treating routine background activity as a new conversation. **IMPLEMENTED.**
7. **Outbound working artifacts** — server-side JANUS-generated research notes/reports/exports as account-bound files, building on authenticated file storage. **IMPLEMENTED.**
8. **Visual explanation decision layer** — decide when an explanatory image/diagram materially improves a user answer; use existing bounded Stage-1 image generation and caching rather than autonomous render loops. **IMPLEMENTED.**
9. **Revenue-gated multi-core visual deliberation scaffolding** — concept/critique/selection records and hard budgets, with actual autonomous background rendering remaining disabled until explicitly enabled economically. **IMPLEMENTED; RENDERING REMAINS DISABLED.**
10. **Research-question workspace for the JANUS mathematical/physical programme** — seed durable audited/open/negative-result questions from project memory so scientific work can accumulate evidence and falsifications without confusing hypotheses with established results. **IMPLEMENTED.**
11. **Reliability/security/soak audit** — cross-account isolation, persistence/migration, background repetition, cost bounds, crash recovery, schema upgrades and end-to-end server deployment checks. **IMPLEMENTED; CI/SOAK VALIDATION IN PROGRESS.**

## Step 11 implementation

`reliability_audit.py` adds a non-destructive audit layer over the persisted server state. It checks SQLite integrity, WAL/recovery mode, required schema presence, foreign-key integrity, account/profile scoping, duplicate-open continuity pressure, repeated-search pressure, cost-ledger sanity and explicit schema-version tracking. The audit never repairs, deletes, compacts or rewrites user content; it records only bounded audit summaries and reliability schema metadata.

Authenticated `/reliability/status` and `/reliability/history` routes expose the current user's audit status/history without publishing other users' data. `image_response_compat.py` installs the router in the live server stack.

`tests/test_reliability_audit.py` covers non-destructive behavior, restart persistence, profile-isolated audit history and duplicate detection without auto-repair. `.github/workflows/test-reliability.yml` runs the reliability-critical regression set and a 12-cycle restart-style soak test against one persistent SQLite database. This supplements, rather than replaces, the existing auth/routing/files/curiosity workflows.

## Previous completed layers

Steps 1-10 remain as implemented in their corresponding modules: continuity ledger/governance, selective federated sync, unified cost governor, maintenance proposals, proactive threads, outbound artifacts, visual explanation gating, disabled-render visual deliberation scaffolding and the epistemically typed JANUS research workspace. Historical design details remain in earlier project checkpoints and module tests.
