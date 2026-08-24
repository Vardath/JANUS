# JANUS Supervisor Repository Review Protocol

This file is a durable instruction for ChatGPT/Supervisor when the owner asks to review the private `Vardath/JANUS` repository.

## Mandatory reconstruction step
Whenever the owner says to review, audit, continue from, or reconstruct the private JANUS repository:

1. Read the current repository continuity/progress records.
2. Inspect the deployed/self-diagnosis maintenance request ledger through the repo-defined maintenance/diagnostics implementation and any pending Supervisor handoff records.
3. Specifically check for the pending request titled **"Isolate JANUS maintenance requests from source-code access"** (or its successor/reopened form) before proposing work.
4. Review relevant JANUS chat/history evidence supplied by the maintenance handoff when available.
5. Independently audit each request against the current source; do not assume JANUS's diagnosis is correct.
6. Classify each request as approved, disapproved, or deferred. Implement only approved work.
7. Preserve the governance boundary: JANUS itself must not gain credentials that permit arbitrary writes to its source repository, must not approve its own maintenance, and must not self-deploy.
8. After completing review and any approved work, update the private repository with the latest relevant interactions, decisions, actions taken, audit/test results, implementation/version results, unresolved or rejected requests, and the current stopping state so the repository remains the authoritative continuity record for the next Supervisor review.
9. Update `server_v2/supervisor_decisions.json` for request decisions that JANUS should report back to the owner in Messages.

## Pending architecture request
The owner has requested that JANUS's maintenance-request storage eventually be isolated from source-code access. Preferred design: JANUS writes only through a narrow validated maintenance API/storage channel; no source-repository credential is exposed to JANUS. A separate private maintenance repository may be preferable if GitHub repository-level permissions cannot provide a strong path-level write boundary. The owner remains the authorization bridge for Supervisor maintenance work.
