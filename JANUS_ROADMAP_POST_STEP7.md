# JANUS post-Step-7 roadmap

Updated 2026-08-22. Windows/PC and Apple client parity are intentionally skipped for this sequence. Android feature work is not a dedicated roadmap step; server/protocol changes should remain backward-compatible where practical.

## Ordered implementation plan

1. **Project + Question Continuity Ledger** — durable lifecycle for projects, questions, tasks, promises, ideas and research; explicit open/completed/deferred/superseded/contradicted states so JANUS can distinguish unfinished work from history. **COMPLETE.**
2. **Continuity integration + contradiction/revision governance** — connect the ledger to Chat, Memory/Context, deliberation and background cognition; detect completion/correction/supersession candidates conservatively; never silently rewrite protected identity/core history. **COMPLETE.**
3. **Federated selective memory synchronization** — formal local/global exchange objects, provenance, conflict detection, merge/supersession rules, bounded remote summaries and no whole-state overwrite. **COMPLETE.**
4. **Unified cost/accounting governor** — per-profile/per-capability usage ledger and configurable daily/monthly budgets for chat escalation, curiosity, background review/synthesis, vision and image generation; graceful throttling before limits. **IMPLEMENTED; CI/live accounting validation pending.**
5. **Maintenance/upgrade request system** — approximately quarterly stack/security/model/dependency review that creates a proposal/report for the user; no autonomous protected-code modification. Email/report delivery can be layered on available account notification infrastructure. **IMPLEMENTED; CI/live notification configuration validation pending.**
6. **Richer proactive thread continuity** — Messages can refer back to the originating question/project/deliberation, distinguish notification from continuation, and avoid treating routine background activity as a new conversation.
7. **Outbound working artifacts** — server-side JANUS-generated research notes/reports/exports as account-bound files, building on authenticated file storage; avoid client-specific parity work in this sequence.
8. **Visual explanation decision layer** — decide when an explanatory image/diagram materially improves a user answer; use existing bounded Stage-1 image generation and caching rather than autonomous render loops.
9. **Revenue-gated multi-core visual deliberation scaffolding** — concept/critique/selection records and hard budgets, with actual autonomous background rendering remaining disabled until explicitly enabled economically.
10. **Research-question workspace for the JANUS mathematical/physical programme** — seed durable audited/open/negative-result questions from project memory so scientific work can accumulate evidence and falsifications without confusing hypotheses with established results.
11. **Reliability/security/soak audit** — cross-account isolation, persistence/migration, background repetition, cost bounds, crash recovery, schema upgrades and end-to-end server deployment checks.

## Step 1 complete

`continuity_ledger.py` provides account/profile-scoped durable project/question state plus append-only lifecycle events. `continuity_api.py` exposes the ledger and binds explicit persistent deliberations into it. Chat receives open continuity state as primary grounding alongside whole-history memory and the 11-core society.

## Step 2 complete

`continuity_governance.py` adds conservative lifecycle interpretation for explicit user statements such as completing, resolving, deferring, contradicting, cancelling or reopening tracked work. Automatic mutation requires a high-confidence subject match. Pronoun-only or weak/ambiguous references never silently change state; they return candidate items for clarification instead.

`interface_chat.py` applies explicit governance before deliberation, then provides both open continuity and authoritative currentness metadata to all core reasoning and the final Interface. Old retained memories remain available as history, but completed/superseded/contradicted lifecycle items must not be presented as still current merely because an older memory mentions them.

## Step 3 complete

`federated_sync.py` introduces typed selective sync records with stable origin ids, device provenance, source timestamps, confidence, lifecycle state, content hashes and explicit merge policy. Remote records are bounded and account/profile-scoped. Protected `identity_core`, system/policy/auth/secret records are rejected rather than merged.

The same origin record updates in place; distinct-device records remain distinct. Similar records that disagree in lifecycle state or claim polarity are not resolved by last-writer-wins: they are marked conflicted and an append-only conflict record is created for later review.

`core_sync.py` remains backward-compatible with legacy `memories`/`conclusions` while accepting optional `sync_records`. Accepted typed records enter the server society only as external grounding routed through Evidence, Context, Memory, Counterpoint and Safety. The heartbeat response returns bounded records from other devices with `grounding_only_no_overwrite`; a device never receives its own record as an overwrite command.

## Step 4 implementation

`cost_governor.py` is the single account/profile budgeting ledger for external compute. It records estimated spend, model identity and provider token usage when available across chat, foreground multi-core consultations, background model/web work, vision and image generation. Limits are configurable by environment and include per-profile daily/monthly, optional-background daily and global daily ceilings.

`cost_governor_hooks.py` applies capability scopes around the existing OpenAI client paths without duplicating budget policy in each subsystem. Optional background work has its own tighter budget so it is denied before ordinary foreground Chat is starved. Cached visual/image results continue to avoid new provider calls and therefore do not create new paid-call events.

`image_response_compat.py` activates the governor in the live bootstrap stack, scopes each authenticated chat turn to its profile, exposes `/desktop/cost-status`, and returns a human-readable cost-governor snapshot with chat responses. The estimates are explicitly labeled planning values rather than provider invoices.

`tests/test_cost_governor.py` covers accounting, per-profile isolation, hard daily limits, background-first throttling and nested capability scopes. The cognition CI compiles and runs the unified governor.

## Step 5 implementation

`maintenance_review.py` now turns the existing quarterly check into a durable, owner-gated maintenance proposal. Roughly every 90 days it captures a zero-model-call runtime snapshot, prepares a structured review across security, runtime/dependencies, model/API changes, clients, architecture and regression testing, and records the proposal as `awaiting_owner_review`.

The proposal explicitly forbids automatic protected-code edits, dependency upgrades, model/API switches and deployment. It stores an email subject/body even when SMTP is not configured, so the request is still recoverable. If `JANUS_MAINTENANCE_OWNER_EMAIL` and SMTP are configured, the email is sent; if `JANUS_MAINTENANCE_OWNER_PROFILE` is configured, a persistent JANUS Messages follow-up is also created for that owner profile.

Owner/admin disposition can be recorded as reviewed, approved-for-manual-work, deferred or rejected, but acknowledgement still performs no maintenance automatically. The intended workflow remains: JANUS requests review -> owner + ChatGPT inspect current technology/security/deprecations -> explicit changes are chosen -> ordinary tested commits/deployments are performed.

`tests/test_maintenance_review.py` verifies advisory-only invariants, stored email drafts, owner-message creation and acknowledgement without self-upgrade. Cognition CI compiles and runs the maintenance tests.
