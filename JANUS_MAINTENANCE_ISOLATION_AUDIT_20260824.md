# JANUS maintenance isolation audit — 2026-08-24

## Owner request
Proceed with the pending Supervisor request **Isolate JANUS maintenance requests from source-code access**, while preserving the owner as the authorization bridge and preserving thorough repo reconstruction/verification.

## Supervisor decision
**APPROVED with a narrow server-side boundary.** JANUS does not receive GitHub credentials and does not write maintenance requests directly to the source repository. Requests remain in JANUS-owned persistent server database storage. Source review/change remains a separate Supervisor action initiated by the owner.

## Implementation
- Added `server_v2/maintenance_channel.py` as the only public client/tool submission boundary used by `/maintenance/diagnostics/report`.
- The channel accepts bounded diagnostic fields only and delegates persistence to the existing capability-request ledger.
- It contains no GitHub/repository client, arbitrary filesystem write, shell/process execution, package installation, configuration mutation, maintenance-decision write, or deployment primitive.
- `/maintenance/status`, `/maintenance/requests`, `/maintenance/supervisor-handoff`, and diagnostic-report responses expose the boundary capabilities explicitly so the security contract is inspectable rather than implicit.
- Added `tests/test_maintenance_channel_isolation.py` to lock the no-source/no-execution boundary against regression.
- Added the Supervisor APPROVED decision keyed by the seeded request fingerprint to `server_v2/supervisor_decisions.json`; after deployment the normal decision importer should mark the matching JANUS request implemented and send the owner a Supervisor-decision Message.

## Important qualification
This is a strong application-level capability boundary, not an operating-system sandbox between Python modules. The deployed server process necessarily contains its own application source in the container. JANUS-facing runtime/API paths are not given a primitive that reads/writes that source or GitHub. If future threat modelling requires protection against arbitrary code execution inside the server process itself, move the maintenance inbox into a separately deployed service/repository/account with its own credential boundary.

## Verification required before completion
1. Server tests, especially maintenance/diagnostics/auth/protocol suites.
2. New maintenance isolation regression test.
3. Confirm no Android regression is introduced; no Android source is changed in this pass, so APK version bump is not required solely for this server-side change.
4. Merge only after CI is green.
5. After merge, verify `main` contains the channel and decision record.
6. Verify deployment/runtime when evidence is available; decision import is not considered proven merely by merge.

## Current stopping state
Implementation is on branch `maintenance-isolation-v109` pending PR/CI/merge verification. Do not describe the request as deployed until those checks complete.
