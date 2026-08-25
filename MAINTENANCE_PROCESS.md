# JANUS maintenance process

This file is a mandatory runbook for every ChatGPT Supervisor maintenance pass. The owner should not need to restate these instructions.

## Canonical maintenance command

When JANUS presents a maintenance handoff, follow this command:

> Review `CURRENT_CHECKPOINT.md`, the current project-status record, this `MAINTENANCE_PROCESS.md`, the private repository, the complete retained JANUS handoff/history, and every open JANUS maintenance/capability request. Treat JANUS-generated request storage as append-only during normal operation. Approve, disapprove, or defer each request independently; implement only approved changes; preserve owner control and all architecture/safety invariants; run all affected regression/build gates; record each decision and implementation result in `server_v2/supervisor_decisions.json`; update repo progress/checkpoints; then reconcile the persistent JANUS maintenance request ledger so only requests that are IMPLEMENTED or DISAPPROVED are removed. Keep DEFERRED, PENDING, repeated, and unresolved requests. Never replace the ledger with a newly generated file and never delete unresolved requests merely because they are old or duplicated.

## Request-ledger rule

JANUS-generated maintenance observations are appended to the persistent JSONL ledger. Normal JANUS operation must **never overwrite** this file.

Default deployed path:

`/data/janus_maintenance_requests.jsonl`

Configured with:

`JANUS_MAINTENANCE_REQUEST_FILE=/data/janus_maintenance_requests.jsonl`

The SQLite capability-request table remains the structured state source; the JSONL ledger is the durable chronological Supervisor/human record. Repeated observations are intentionally retained until the corresponding request is resolved.

## Required Supervisor sequence

1. Read `CURRENT_CHECKPOINT.md` and the current status/progress record before editing code.
2. Read this file and run/observe the maintenance handoff command; do not rely on remembered procedure.
3. Review every open request against the current source, tests, runtime evidence, retained history, and project plans.
4. Decide each independently: `approved`, `disapproved`, or `deferred`.
5. Implement only approved changes. JANUS itself never approves or deploys maintenance.
6. Run the relevant clean-server, protocol, auth, maintenance, recursive-core, Android Java/APK, RC, UI/localization, and other affected gates.
7. Update `server_v2/supervisor_decisions.json` with a stable decision key, request ID/fingerprint, decision, reason, implementation state, and implemented version/commit.
8. Update `CURRENT_CHECKPOINT.md` and the current project-status/progress record with completed work, unresolved risks, and next tasks.
9. Reconcile the maintenance request ledger. Remove entries only when their current request state is `implemented` or `disapproved`. Retain `deferred`, `awaiting_supervisor_review`, pending, repeated, malformed/manual, and unresolved entries.
10. Confirm the owner-facing JANUS Messages path can report applied Supervisor decisions after deployment.

## Built-in ledger commands

Print these instructions:

`python -m server_v2.maintenance_request_file instructions`

Show ledger status:

`python -m server_v2.maintenance_request_file status`

Print retained/open ledger entries:

`python -m server_v2.maintenance_request_file print-open`

Reconcile after decisions have been applied:

`python -m server_v2.maintenance_request_file reconcile`

On normal deployment, `server_v2/supervisor_decisions.json` is consumed at startup and the same closed-request reconciliation is performed automatically. This means an approved-and-implemented or disapproved request is removed from the active persistent request ledger after its decision reaches the deployed server, while unresolved requests remain.

## Non-negotiable boundaries

JANUS may diagnose and request maintenance, but it may not edit its own code, install packages, change model/API configuration, approve requests, merge code, or deploy itself. Supervisor work remains owner-gated. Maintenance must preserve account isolation, protected identity/core memory, selective no-overwrite federation, background cost controls, the strict seven -> Left/Right -> Front -> Interface outward route, passive interruptible rest, loop-quiescence guards, and the no-phenomenal-consciousness-claim boundary.
