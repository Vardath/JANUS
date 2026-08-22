# JANUS Phase 2 Release Checkpoint

This checkpoint freezes the Phase 2 stabilization work long enough to validate the integrated server + Android system before another feature phase begins.

## Baseline

- Server architecture: 11-core JANUS society, 7 specialists → 2 hemispheres → consensus → interface.
- Android baseline: v0.69.
- Server/local synchronization: selective typed records with provenance; no whole-state overwrite.
- Memory: whole-history retrieval over persisted user-visible records, correction precedence, continuity-marker promotion, duplicate suppression.
- Background cognition: usefulness gate suppresses repetitive/process-heavy autonomous research before external spend.
- External-compute governance: foreground/background/image/vision accounting with graceful degradation and provider-failure classification.
- Owner observability: human-readable server/local/memory/cost/provider status.
- Quarterly maintenance: proposal-only review path; no autonomous self-modification.

## Release invariants

1. Authenticated identity, never a client-supplied username, owns private profile state.
2. Existing durable schemas are checked before ordinary writes; incompatible legacy shapes fail closed.
3. Local and global JANUS states remain independent and synchronize selectively.
4. Protected identity/core policy cannot be overwritten through federated records.
5. Conflicting remote claims remain visible and provenance-preserving rather than being silently resolved.
6. Failed provider calls do not consume successful-call budget estimates.
7. Optional background work degrades before foreground Chat.
8. Background image deliberation remains non-rendering; explicit foreground image generation stays bounded by image policy and budget.
9. Persisted conversation/memory records may be retrieved; hidden chain-of-thought is never exported as memory or diagnostics.
10. Owner diagnostics must distinguish server health from local-device presence.

## Deferred at this checkpoint

- Windows/desktop client consolidation and packaging.
- Apple/iOS client parity work.
- Autonomous background image rendering remains disabled.
- Revenue-gated expansion of background visual collaboration remains deferred.
- Any new physical/cosmological claims remain separate from the audited JANUS mathematical research workspace.

## Validation gate

The dedicated `Phase 2 Release Checkpoint` GitHub Actions workflow must pass both jobs:

- **server-stability** — reconstructs the deployed server, compiles critical modules, runs auth/security, persistence, cognition, memory, sync, cost/failure, observability, artifact and visual-policy regressions.
- **android-v069** — applies the consolidated Android patch and assembles v0.69 from a clean runner.

A red checkpoint means Phase 2 is not considered stable until the failing assumption or implementation is corrected. Historical red runs are retained as evidence; fixes should be additive and must not roll back unrelated completed work.

## Release state

Implementation checkpoint created. CI validation pending.
