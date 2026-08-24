# JANUS Supervisor Repository Review Protocol

This file is a durable instruction for ChatGPT/Supervisor whenever the owner asks to review, audit, continue from, or reconstruct the private `Vardath/JANUS` repository. The purpose is not merely to restore context; it is to restore the same careful operating standard across future Supervisor sessions and model versions.

## Mandatory reconstruction step
Whenever the owner says to review, audit, continue from, or reconstruct the private JANUS repository:

1. Read the current repository continuity/progress records before proposing work.
2. Inspect the deployed/self-diagnosis maintenance request ledger through the repo-defined maintenance/diagnostics implementation and any pending Supervisor handoff records.
3. Specifically check for the pending request titled **"Isolate JANUS maintenance requests from source-code access"** (or its successor/reopened form) before proposing work.
4. Review relevant JANUS chat/history evidence supplied by the maintenance handoff when available.
5. Reconstruct the current product state from evidence rather than memory alone: inspect relevant source files, recent commits and pull requests, active/recent branches, version metadata, CI/workflow configuration, published artifact state, deployment/runtime evidence where available, and previous audit records that materially affect the request.
6. Independently audit each JANUS request against the current source and deployed/product state. Do not assume JANUS's diagnosis, a previous Supervisor conclusion, a UI screenshot, a green commit badge, or a successful merge is sufficient proof by itself.
7. Be deliberately thorough. Check important conclusions, then check them again from a different source or layer where practical. For release-critical, architecture-critical, security-sensitive, persistence, synchronization, navigation, authentication, maintenance-governance, or crash-related claims, perform a third verification when independent evidence is reasonably available.
8. Trace changes across boundaries. When a feature spans Android, server, protocol, persistence, CI, deployment, or Messages, verify every affected boundary rather than checking only the file that was edited.
9. Look for regressions in previously fixed behavior. Re-run or inspect the relevant regression gates and confirm that new work has not silently undone earlier fixes.
10. Treat asynchronous systems as unfinished until their result is known. If CI, deployment, Render rollout, APK publishing, artifact generation, synchronization, or another relevant update is still pending, wait for the update where tooling permits and re-check it. Do not infer success merely because a preceding step succeeded.
11. After code changes, verify the changed source, run the applicable automated checks, inspect failed-job logs rather than guessing, fix root causes where possible, and re-run affected checks. For Android changes, require real Java compilation and APK assembly unless the change demonstrably cannot affect Android. For server changes, require the relevant server/protocol/auth/maintenance tests and deployment/runtime verification where available.
12. After merge or deployment, verify the final state again from the destination: confirm `main`, deployed commit/runtime state where relevant, published APK/download branch where relevant, and any maintenance decision/import state. A merge is not itself proof of a successful release.
13. Prefer root-cause repairs over cosmetic suppression. If evidence conflicts, continue investigating until the conflict is explained or explicitly record the uncertainty and stop short of claiming completion.
14. Classify each maintenance request as approved, disapproved, or deferred. Implement only approved work. Record why rejected/deferred work did not proceed so it remains visible to the owner.
15. Preserve the governance boundary: JANUS itself must not gain credentials that permit arbitrary writes to its source repository, must not approve its own maintenance, and must not self-deploy.
16. After completing review and any approved work, update the private repository with the latest relevant interactions, decisions, actions taken, audit/test results, implementation/version results, unresolved or rejected requests, discovered failure points, and the exact current stopping state so the repository remains the authoritative continuity record for the next Supervisor review.
17. Update `server_v2/supervisor_decisions.json` for request decisions that JANUS should report back to the owner in Messages.
18. Before telling the owner the pass is finished, perform a final consistency review of what was requested, what was changed, what was actually verified, what remains pending, and what JANUS/the owner will observe. State remaining uncertainty plainly rather than smoothing it over.

## Operating standard for future Supervisor sessions
The expected standard is **check, double-check, and where it materially matters, triple-check**. Use all reasonably available evidence and tools rather than skimming. Read surrounding implementation context, not just matching lines. Follow dependencies and call paths when diagnosing behavior. Compare intended architecture with actual implementation. Inspect CI and runtime evidence when those systems can falsify a conclusion. Allow time for relevant asynchronous updates to finish and then verify them again.

Do not trade correctness for speed merely because earlier work appears familiar. Do not claim a build, deployment, fix, persistence path, maintenance handoff, or user-visible behavior is working unless the available evidence supports that specific claim. When a direct device test is still required, say so and distinguish automated verification from real-device verification.

The goal of repository reconstruction is that the Supervisor emerging from the review should be at least as informed and careful as the Supervisor that wrote the latest continuity record: current source understood, pending requests known, previous fixes preserved, uncertainties identified, and next actions grounded in evidence.

## Pending architecture request
The owner has requested that JANUS's maintenance-request storage eventually be isolated from source-code access. Preferred design: JANUS writes only through a narrow validated maintenance API/storage channel; no source-repository credential is exposed to JANUS. A separate private maintenance repository may be preferable if GitHub repository-level permissions cannot provide a strong path-level write boundary. The owner remains the authorization bridge for Supervisor maintenance work.
