# JANUS Step 9 — revenue-gated multi-core visual deliberation scaffolding

Updated: 2026-08-22

## Status

Implemented as scaffolding only. Autonomous/background image rendering remains disabled.

## What now exists

- Account-bound persistent visual-deliberation runs.
- Externalizable record types: `concept`, `critique`, and `selection`.
- JANUS core attribution for the seven specialists, two hemispheres, Consensus, and Interface.
- Candidate ids and bounded revision numbers so multiple proposed visual structures can be compared without creating render loops.
- Hard per-run concept, critique, revision, total-record, and per-account open-run limits.
- Only Consensus or Interface may record a final selection.
- Account isolation for both deliberation runs and records.
- Authenticated server routes under `/visual-deliberations` for policy, start, list, inspect, and record operations.

## Economic/rendering boundary

`visual_deliberation.py` deliberately imports no image renderer and performs no model/API call. `AUTONOMOUS_RENDERING_ENABLED` is hard false in Step 9 even if an environment variable is accidentally set.

The policy reports both a future revenue-gate flag and a future rendering-request flag, but those flags cannot activate rendering in this implementation. Enabling autonomous multi-core rendering requires a later explicit code change after economics justify it.

The existing Stage-1 foreground image path remains separate: explicit user image requests and rare Interface-nominated explanatory visuals may still use the bounded/cached image generator under its existing cost policy.

## CI

`tests/test_visual_deliberation.py` verifies:

- scaffolding is active while rendering stays disabled;
- concept → critique → selection records are persisted and externalizable;
- only Consensus/Interface may select;
- revision/concept limits are enforced;
- cross-account access is rejected.

The main cognition workflow compiles `visual_deliberation.py` and runs these regressions.

## Next roadmap step

Step 10: create a durable research-question workspace for the JANUS mathematical/physical programme, seeded from the audited project memory and clearly separating established mathematics, hypotheses, open questions, falsification tests, and negative results.
