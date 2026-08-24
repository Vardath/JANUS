# JANUS maintenance isolation audit — 2026-08-24

## Owner request
Proceed with the pending Supervisor request **Isolate JANUS maintenance requests from source-code access**, while preserving the owner as the authorization bridge and preserving thorough repo reconstruction/verification.

## Supervisor decision
**APPROVED with a narrow server-side boundary.** JANUS does not receive GitHub credentials and does not write maintenance requests directly to the source repository. Requests remain in JANUS-owned persistent server database storage. Source review/change remains a separate Supervisor action initiated by the owner.

## Implementation
- Added `server_v2/maintenance_channel.py` as the public client/tool submission boundary used by `/maintenance/diagnostics/report`.
- The channel accepts bounded diagnostic fields only and delegates persistence to the existing capability-request ledger.
- It contains no GitHub/repository client, arbitrary filesystem write, shell/process execution, package installation, configuration mutation, maintenance-decision write, or deployment primitive.
- `/maintenance/status`, `/maintenance/requests`, `/maintenance/supervisor-handoff`, and diagnostic-report responses expose the boundary capabilities explicitly so the security contract is inspectable rather than implicit.
- Added `tests/test_maintenance_channel_isolation.py` and wired it into the Maintenance Review CI gate to lock the no-source/no-execution boundary against regression.
- Added the Supervisor APPROVED decision keyed by the seeded request fingerprint to `server_v2/supervisor_decisions.json`; after deployment the normal decision importer should mark the matching JANUS request implemented and send the owner a Supervisor-decision Message.

## Important qualification
This is a strong application-level capability boundary, not an operating-system sandbox between Python modules. The deployed server process necessarily contains its own application source in the container. JANUS-facing runtime/API paths are not given a primitive that reads/writes that source or GitHub. If future threat modelling requires protection against arbitrary code execution inside the server process itself, move the maintenance inbox into a separately deployed service/repository/account with its own credential boundary.

## Verification performed
1. PR #22 Maintenance Review CI passed with the new isolation test included explicitly.
2. Clean server-v2 CI passed.
3. Auth CI passed.
4. Android regression/build CI passed: v1.08 governance, v1.07 chrome/Back/Cores, v1.06 thought/Fano, v1.04 Chat performance gates, real Java compilation, and debug APK assembly all succeeded. APK publication was correctly skipped on the PR build.
5. PR #22 was merged only after those gates were green; merge commit `bb526c369e20f089dbda265b9fba6470cdb6cb9d`.
6. Post-merge `main` was re-read and confirmed to contain `server_v2/maintenance_channel.py` with the intended restricted capability contract.

## Current stopping state
The source change is merged and CI-verified on `main`. No Android source/version changed in this pass, so users do not need a new APK solely for this server-side governance hardening. Production deployment/decision-import is **not yet claimed verified** from the available evidence; the Supervisor decision should be considered pending runtime import until the deployed server consumes it and JANUS exposes/sends the resulting decision state. Future repo review must check that state rather than assuming merge implied deployment.
