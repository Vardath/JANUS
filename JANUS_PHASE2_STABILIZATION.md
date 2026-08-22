# JANUS Phase 2 — Stabilization, hardening and evidence

The original post-Step-7 implementation roadmap (Steps 1–11) is functionally complete. This phase is deliberately different: prefer system-level correctness, evidence, integration quality and bounded behavior over adding more features.

## Ordered stabilization plan

1. **Authentication boundary hardening** — ensure every post-security wrapper resolves the authenticated account before any memory, thread, research, cost, file or diagnostic side effect. Client-supplied `username`/`profile_id` must never select another account's partition. **IMPLEMENTED; CI validation pending.**
2. **Route/security inventory** — enumerate all profile/account-bearing routes and prove each is public-by-design, admin-token-bound or account-session-bound. Remove accidental query-parameter identity selectors from private endpoints. **IMPLEMENTED; CI validation pending.**
3. **Persistence and migration matrix** — record schema ownership/version for every durable table, test clean install + legacy upgrade + repeated restart paths, and detect incompatible old schemas before accepting writes. **IMPLEMENTED; CI validation pending.**
4. **Background usefulness audit** — measure useful novel outputs versus repetition/self-reference; suppress low-information loops and keep curiosity/research budget focused on concrete questions and evidence. **IMPLEMENTED; CI validation pending.**
5. **Memory quality audit** — test conversation-thread retention, corrections, contradictions, salience promotion, duplicate consolidation and whole-history retrieval on realistic multi-session conversations. **IMPLEMENTED; CI validation pending.**
6. **Server/local synchronization soak** — long-running selective-sync tests covering reconnects, duplicate devices, stale clients, conflict provenance, no-overwrite guarantees and heartbeat loss/recovery.
7. **Cost/failure degradation audit** — exercise exhausted web/model/image budgets, provider timeouts, malformed responses and partial outages; ordinary chat and deterministic local/server cognition should degrade cleanly.
8. **Operational observability** — expose human-readable owner/admin health summaries for reliability, budgets, migrations, synchronization and background usefulness without leaking private account content.
9. **Release checkpoint** — freeze feature additions briefly, run the full suite/soak matrix, document known limitations, and create a stable server protocol checkpoint before returning to optional new features.

## Phase 2 Step 1

`image_response_compat.py` authenticates before any profile-scoped thread, research, memory or cost work. The authenticated username replaces client-selected identity fields before side effects, and `/desktop/cost-status` is session-bound.

## Phase 2 Step 2

`secure_desktop.py` and late-installed thread routes now bind private profile/account APIs to authenticated sessions. `JANUS_ROUTE_SECURITY_INVENTORY.md` records the public/admin/account boundary classes.

## Phase 2 Step 3

`persistence_matrix.py` registers minimum compatible durable schemas, tolerates additive columns, rejects incompatible existing shapes before ordinary writes, and records the observed matrix after initialization.

## Phase 2 Step 4

`background_usefulness.py` adds a deterministic zero-API gate before autonomous research spending, suppressing repetitive/process-heavy self-reference while leaving explicit foreground research untouched. It records account-scoped usefulness metrics for inspection.

## Phase 2 Step 5

`memory_quality.py` adds deterministic whole-history retrieval over retained user-visible conversation records rather than relying only on the latest fixed-size Chat window. Relevant older material can re-enter the live Chat prompt through a concise persisted `memory_context` record, while ordinary recent conversation remains intact.

User corrections and clarifications are explicitly marked with precedence over earlier conflicting material. Phrases such as “think about this”, “ponder”, “mull it over”, “remember this” and “come back to this” are treated as continuity markers and receive gentle trace→working→episodic reinforcement instead of being discarded as ordinary transient turns. Long substantive user turns also receive a conservative trace→working promotion.

Exact repeated user turns are measured and near-identical retrieved memories are collapsed from the injected context so repetition cannot crowd out independent older history. Retrieval is profile-scoped, does not promote unrelated material merely because it was searched, and never exposes hidden chain-of-thought: only persisted conversation/memory records are eligible.

`/memory-quality/status` exposes account-scoped audit counts, and `janus_memory_quality` records reinforcement events. `persistence_matrix.py` registers this table and advances the durable matrix version. `tests/test_memory_quality.py` covers old-history retrieval beyond the recent window, correction precedence, ponder/remember promotion, duplicate suppression, account isolation and non-promotion of irrelevant turns. The main cognition CI compiles and runs the new suite.
