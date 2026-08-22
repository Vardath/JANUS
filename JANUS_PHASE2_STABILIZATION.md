# JANUS Phase 2 — Stabilization, hardening and evidence

The original post-Step-7 implementation roadmap (Steps 1–11) is functionally complete. This phase is deliberately different: prefer system-level correctness, evidence, integration quality and bounded behavior over adding more features.

## Ordered stabilization plan

1. **Authentication boundary hardening** — ensure every post-security wrapper resolves the authenticated account before any memory, thread, research, cost, file or diagnostic side effect. Client-supplied `username`/`profile_id` must never select another account's partition. **IMPLEMENTED; CI validation pending.**
2. **Route/security inventory** — enumerate all profile/account-bearing routes and prove each is public-by-design, admin-token-bound or account-session-bound. Remove accidental query-parameter identity selectors from private endpoints. **IMPLEMENTED; CI validation pending.**
3. **Persistence and migration matrix** — record schema ownership/version for every durable table, test clean install + legacy upgrade + repeated restart paths, and detect incompatible old schemas before accepting writes.
4. **Background usefulness audit** — measure useful novel outputs versus repetition/self-reference; suppress low-information loops and keep curiosity/research budget focused on concrete questions and evidence.
5. **Memory quality audit** — test conversation-thread retention, corrections, contradictions, salience promotion, duplicate consolidation and whole-history retrieval on realistic multi-session conversations.
6. **Server/local synchronization soak** — long-running selective-sync tests covering reconnects, duplicate devices, stale clients, conflict provenance, no-overwrite guarantees and heartbeat loss/recovery.
7. **Cost/failure degradation audit** — exercise exhausted web/model/image budgets, provider timeouts, malformed responses and partial outages; ordinary chat and deterministic local/server cognition should degrade cleanly.
8. **Operational observability** — expose human-readable owner/admin health summaries for reliability, budgets, migrations, synchronization and background usefulness without leaking private account content.
9. **Release checkpoint** — freeze feature additions briefly, run the full suite/soak matrix, document known limitations, and create a stable server protocol checkpoint before returning to optional new features.

## Phase 2 Step 1

`image_response_compat.py` previously wrapped the already-secured `/desktop/chat` route but performed thread lookup, research-context storage and cost accounting using the client-supplied `profile_id`/`username` before invoking the secure inner route. That could allow cross-profile side effects even though the final chat implementation itself was session-bound.

The wrapper now resolves identity through `secure_desktop._profile()` before any profile-scoped work. The authenticated username overwrites client identity fields in a copied payload before thread lookup, research grounding, cost scope and the inner chat call. `/desktop/cost-status` is likewise session-bound and no longer accepts an arbitrary username query selector.

`tests/test_profile_boundary_hardening.py` guards the normalization contract and the cost-status signature. The main cognition CI now compiles the security wrapper and runs these regressions.

## Phase 2 Step 2

A route-by-route inventory found several older `/desktop/*` APIs whose implementation functions still accepted client-selected usernames even though the primary Chat/Memory/Message surfaces had already been secured. The affected externally reachable surfaces included continuity lifecycle/history, detailed core observation, hive budget, core-research status, autonomous-message quality and self-assessment telemetry.

`secure_desktop.install()` now captures those legacy implementations and re-exposes them only through authenticated wrappers. Reads derive the profile from the session; continuity writes overwrite any supplied `profile_id`/`username` in a copied payload before forwarding it. Self-assessment remains global operational telemetry but now requires an authenticated account rather than being anonymously readable.

A second issue existed in routes installed later by `bootstrap.py`: proactive Message thread diagnostics were created after the main secure-desktop pass and still accepted a `username` query selector. `proactive_threads.py` now authenticates those routes internally through `auth.require_account()` and derives the profile from that account. Old clients may still send an unused username query parameter, but it is no longer part of the route contract and cannot select a partition.

`JANUS_ROUTE_SECURITY_INVENTORY.md` records the explicit boundary classes: public-by-design, administrator-token-bound, router-authenticated account APIs, secure-desktop compatibility wrappers and late-installed internally authenticated routes. `tests/test_profile_boundary_hardening.py` now protects these route contracts in CI.
