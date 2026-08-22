# JANUS Phase 2 — Stabilization, hardening and evidence

The original post-Step-7 implementation roadmap (Steps 1–11) is functionally complete. This phase is deliberately different: prefer system-level correctness, evidence, integration quality and bounded behavior over adding more features.

## Ordered stabilization plan

1. **Authentication boundary hardening** — authenticated identity owns every private profile side effect. **IMPLEMENTED.**
2. **Route/security inventory** — classify public/admin/account routes and remove client-selected private identity selectors. **IMPLEMENTED.**
3. **Persistence and migration matrix** — register durable schemas and fail closed on incompatible existing shapes before ordinary writes. **IMPLEMENTED.**
4. **Background usefulness audit** — suppress repetitive/process-heavy autonomous research before external spend. **IMPLEMENTED.**
5. **Memory quality audit** — whole-history retrieval, correction precedence, continuity-marker promotion and duplicate suppression. **IMPLEMENTED.**
6. **Server/local synchronization soak** — reconnect, stale heartbeat, multi-device conflicts, restart persistence and no-overwrite guarantees. **IMPLEMENTED.**
7. **Cost/failure degradation audit** — optional work throttles before foreground Chat; provider failures are classified and do not consume successful-call budget estimates. **IMPLEMENTED.**
8. **Operational observability** — human-readable server/local, memory, cost and provider-health summaries; Android v0.69 surfaces this under Options → System status. **IMPLEMENTED.**
9. **Release checkpoint** — integrated server stability + Android v0.69 clean-build gate, known limitations and protocol invariants. **IMPLEMENTED; CI VALIDATION PENDING.**

## Phase 2 Step 1 — Authentication boundary

`image_response_compat.py`, `secure_desktop.py` and late-installed account routes resolve authenticated identity before profile-scoped memory, thread, research, cost, file or diagnostic side effects. Client-supplied `username`/`profile_id` cannot select another private partition.

## Phase 2 Step 2 — Route/security inventory

`JANUS_ROUTE_SECURITY_INVENTORY.md` records public-by-design, administrator-token-bound, router-authenticated and compatibility-wrapper surfaces. Older private desktop diagnostics and continuity routes are session-bound.

## Phase 2 Step 3 — Persistence and migrations

`persistence_matrix.py` registers minimum compatible durable schemas, tolerates additive columns, rejects incompatible existing shapes before ordinary writes, and records the observed matrix after initialization. The auth normalizer remains the only targeted compatibility migration for the oldest account/session layouts.

## Phase 2 Step 4 — Background usefulness

`background_usefulness.py` adds a deterministic zero-API gate before autonomous research spending. Repetitive or JANUS-process-heavy candidates are suppressed before web/model calls; explicit foreground user research remains unaffected. Decisions and completed-result usefulness are retained for account-scoped inspection.

## Phase 2 Step 5 — Memory quality

`memory_quality.py` adds deterministic whole-history retrieval over retained user-visible conversation records rather than relying only on the latest fixed-size Chat window. Relevant older material can re-enter the live Chat prompt through concise persisted memory context while ordinary recent conversation remains intact.

Corrections and clarifications receive precedence over earlier conflicting material. Phrases such as “think about this”, “ponder”, “mull it over”, “remember this” and “come back to this” are continuity markers and receive conservative memory reinforcement. Repeated retrieved memories are collapsed so repetition cannot crowd out independent history. Hidden chain-of-thought is never exported as memory.

## Phase 2 Step 6 — Server/local synchronization soak

The synchronization soak exercises the existing selective-federation contract under repeated reconnect and restart pressure. Remote state arrives as bounded typed grounding records with provenance; neither local nor global state receives a whole-state overwrite instruction.

`tests/test_sync_soak.py` covers stable-device reconnect without duplicate registration, heartbeat expiry and recovery, two-device exchange without origin echo, conflicting claims remaining simultaneously present and marked conflicted, repeated persistence-module reloads, and stable `origin_id` updates in place.

`.github/workflows/test-sync-soak.yml` provides the dedicated synchronization workflow and the main cognition suite also executes these regressions.

## Phase 2 Step 7 — Cost/failure degradation

The external-compute governor distinguishes successful completions from provider timeouts, malformed responses and other upstream failures. Failed provider calls are retained as diagnostics at zero estimated successful-call cost, preventing an outage from manufacturing a budget lockout.

Optional background web/model/maintenance work remains the first class to be throttled. Foreground Chat stays eligible while its own profile/global allowance remains available. Regression tests deliberately simulate exhausted background allowances and repeated provider failures.

## Phase 2 Step 8 — Operational observability

`owner_observability.py` translates raw telemetry into `healthy`, `degraded` or `attention` status with human-readable explanations. It reports server background-cycle health, authenticated local-device presence, retained continuity counts, cost protection and recent provider failures while keeping server and local runtime state distinct.

Android v0.69 adds **Options → System status**, consuming the owner diagnostic and falling back to local JANUS status if the server is unavailable. Windows and Apple client parity remain deferred by design.

## Phase 2 Step 9 — Release checkpoint

`JANUS_PHASE2_RELEASE_CHECKPOINT.md` records the stable protocol invariants and known deferred work. `.github/workflows/phase2-release-checkpoint.yml` is the integrated gate with two independent jobs:

- **server-stability** reconstructs the deployed server, compiles critical modules, runs auth/authorization regressions, then runs the complete Phase 2 cognition/security/persistence/memory/sync/cost/failure/observability/artifact/visual-policy matrix.
- **android-v069** applies the authoritative consolidated Android patch, verifies version 0.69 and performs a clean Gradle debug assembly.

A red checkpoint is evidence that Phase 2 is not yet a stable baseline. Fixes should be narrow and additive; unrelated completed functionality should not be rolled back merely to make the checkpoint green.
