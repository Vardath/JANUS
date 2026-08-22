# JANUS Step 10 checkpoint — research-question workspace

Date: 2026-08-22

Step 10 of the post-Step-7 roadmap is implemented server-side.

## Purpose

JANUS now has a durable, account-scoped scientific workspace that separates exact/audited mathematics from empirical findings, hypotheses, interpretations, open questions, proposed tests, predictions, negative results, boundaries and references. Evidence is appended rather than silently changing epistemic status. Negative results remain durable research results rather than disappearing from future reasoning.

## Seeded JANUS programme

The seed preserves the Closed JANUS mathematical core as audited/non-physical, records the canonical Q operator and Steane/Fano realization as mathematical/quantum-information results, and records major closed-negative branches including the symmetric passive-energy-barrier candidate, literal Solar-System realization and simple Planck/fine-structure derivation.

Open high-priority questions include the physical dictionary, a distinctive observable/prediction, and a concrete dynamics/locality bridge. Proposed tests include alternative passive interaction families, unequal orientation ensembles, order-4/trinity closure and higher-r auditing. The user's cosmological interpretation is explicitly kept as a separate interpretive model rather than being promoted by mathematical recurrence.

## Integration

`research_workspace.py` owns durable claims, evidence and relations. Open questions/tests are mirrored into `continuity_ledger.py` so they can be revisited by the existing project/question continuity machinery.

`image_response_compat.py` injects a bounded research-workspace context into the normal Chat process context when a workspace exists. The context explicitly instructs JANUS to preserve epistemic labels and not present hypotheses/interpretations as established physics.

The authenticated routes are:
- `POST /research/workspace/seed`
- `GET /research/workspace`
- `POST /research/claims`
- `POST /research/claims/{claim_id}/evidence`

Automatic seeding is restricted to the explicitly configured owner profile using `JANUS_RESEARCH_OWNER_PROFILE`; if absent, the existing `JANUS_MAINTENANCE_OWNER_PROFILE` is reused. This avoids copying the creator's private research programme into unrelated accounts.

## Safety/epistemic invariants

- Adding evidence does not automatically upgrade a hypothesis.
- Negative results remain queryable and are not rewritten as open successes.
- Account/profile isolation is mandatory.
- Mathematical results cannot silently become physical claims.
- Explicit state changes are auditable.
- Research seeding failure cannot prevent server/Chat startup.

## CI

`tests/test_research_workspace.py` covers idempotent seeding, epistemic labels, continuity linking, evidence-without-auto-promotion, negative-result preservation, explicit state revision and profile isolation. The main cognition workflow compiles and runs the research workspace suite.

Next roadmap item: Step 11 reliability/security/soak audit.
