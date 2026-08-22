# JANUS Phase 2 — Stabilization, hardening and evidence

The original post-Step-7 implementation roadmap (Steps 1–11) is functionally complete. This phase is deliberately different: prefer system-level correctness, evidence, integration quality and bounded behavior over adding more features.

## Ordered stabilization plan

1. **Authentication boundary hardening** — ensure every post-security wrapper resolves the authenticated account before any memory, thread, research, cost, file or diagnostic side effect. Client-supplied `username`/`profile_id` must never select another account's partition. **IMPLEMENTED; CI validation pending.**
2. **Route/security inventory** — enumerate all profile/account-bearing routes and prove each is public-by-design, admin-token-bound or account-session-bound. Remove accidental query-parameter identity selectors from private endpoints. **IMPLEMENTED; CI validation pending.**
3. **Persistence and migration matrix** — record schema ownership/version for every durable table, test clean install + legacy upgrade + repeated restart paths, and detect incompatible old schemas before accepting writes. **IMPLEMENTED; CI validation pending.**
4. **Background usefulness audit** — measure useful novel outputs versus repetition/self-reference; suppress low-information loops and keep curiosity/research budget focused on concrete questions and evidence. **IMPLEMENTED; CI validation pending.**
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

## Phase 2 Step 3

`persistence_matrix.py` now provides a single minimum-compatibility registry for the main durable JANUS tables. It records each table's owning subsystem, a registry schema version and the columns current code requires. The registry deliberately tolerates extra additive columns rather than demanding byte-for-byte SQL identity.

Startup ordering is now explicit. The existing auth normalizer first preserves the oldest incompatible account layouts; `auth_schema_guard.py` performs safe additive auth fixes and preserves incompatible legacy session/token tables; then `persistence_matrix.preflight_existing()` runs before `janus_dashboard` is imported. A missing table is valid on a clean installation, but an already-existing registered table missing required columns causes a fail-closed degraded startup before ordinary application modules can write through the incompatible shape.

After the normal subsystems have initialized, `image_response_compat.install()` records the observed matrix version and table compatibility snapshot into `janus_schema_meta`. This gives repeated restarts a durable schema checkpoint without rewriting user tables. Outside the pre-existing auth compatibility migrations, the new guard is intentionally non-destructive: it does not guess at unknown legacy conversions, delete rows or silently rebuild tables.

`JANUS_PHASE2_PERSISTENCE_MATRIX.md` documents table ownership and startup policy. `tests/test_persistence_matrix.py` covers clean installation, incompatible legacy shape rejection, additive-column compatibility and repeated restart/idempotence. The cognition CI now compiles and runs the persistence registry tests.

## Phase 2 Step 4

`background_usefulness.py` adds a deterministic, zero-API quality gate in front of autonomous curiosity searches. It scores each proposed background query for concrete subject matter, novelty relative to recent research, process/self-reference density and near-duplicate similarity. Candidates dominated by JANUS cycle/core/Consensus/Interface telemetry or candidates that substantially repeat recent searches are suppressed before the web/model request is scheduled, so rejected loops consume no external research budget.

The gate affects autonomous background search selection only. Foreground user-requested research and explicit Chat questions are not blocked by it. Existing diversity controls in `background_cognition.py` and Message-level filtering in `proactive_quality.py` remain separate downstream safeguards.

The new persistent `janus_background_usefulness` table records accepted/suppressed candidate decisions with numeric novelty, process ratio, similarity, score and human-readable reason labels. Completed research is also audited retrospectively to estimate usefulness rate, repetition and process-heavy output. `/background-usefulness/status` is authenticated and account-scoped, allowing the current user to inspect their own metrics without exposing another profile's material.

`persistence_matrix.py` now registers the usefulness table and advances its matrix version. `tests/test_background_usefulness.py` covers concrete novel research, recursive self-reference suppression, near-duplicate suppression, durable gate decisions, completed-output auditing and installation of the gate onto the background curiosity selector. The main cognition CI compiles the new module and runs the new regressions.
