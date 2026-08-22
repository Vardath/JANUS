# JANUS Step 3 Selective Federated Sync Checkpoint — 2026-08-22

This checkpoint follows the continuity-ledger and contradiction-governance work.

## Step 3 implemented

JANUS now has a formal selective federated synchronization layer rather than relying only on compact runtime summaries and untyped memory strings.

### Protocol

Clients may optionally send `sync_records` on the existing authenticated `/core-sync/exchange` heartbeat. Older clients remain compatible because the field is optional and legacy `memories` / `conclusions` are still accepted as bounded grounding.

Each typed record carries a stable origin id, device provenance, kind, text, lifecycle state, confidence and source timestamp. The server computes a content hash and persists the record account/profile-scoped. Same-device/same-origin updates mutate that record in place rather than duplicating it.

Allowed remote kinds are bounded to memory/conclusion/question/project/research/correction/preference/observation. Protected identity/system/policy/auth/credential/secret material is rejected from federated intake. Remote data cannot overwrite `identity_core` or server safety/policy state.

### No whole-state overwrite

Federated records are explicitly marked `grounding_only_no_overwrite`. The server heartbeat returns only bounded records from other devices, so a device does not receive its own record back as an overwrite command. Existing global Consensus/Interface/deliberation summaries remain separate tagged grounding.

### Conflict handling

The server does not use blind last-writer-wins for distinct-device claims. Similar records that disagree in lifecycle state or claim polarity are retained separately, marked `conflicted`, and linked through an append-only conflict record. They therefore remain reviewable evidence rather than silently erasing one another.

### Cognitive routing

New accepted remote typed records are routed through Evidence, Context, Memory, Counterpoint and Safety before integration. Conflicted records are explicitly labelled as conflicted grounding. Remote material never injects directly into Consensus/Interface as authoritative state.

### Tests

`tests/test_federated_sync.py` covers:
- device provenance and bounded no-echo outbound behavior;
- rejection of protected identity/core kinds;
- conflict creation without overwrite;
- same-origin update-in-place semantics;
- account/profile isolation.

The cognition CI workflow now compiles `federated_sync.py` and `core_sync.py` and runs the federated regression suite.

## Next roadmap step

Step 4 is the unified cost/accounting governor: record and enforce per-profile/per-capability budgets across foreground model use, curiosity/search, background review/synthesis, vision and image generation, with graceful throttling rather than surprise overspend.
