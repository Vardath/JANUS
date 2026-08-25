# JANUS live recovery / CI cleanup checkpoint — 2026-08-25

## Trigger

Android real-device test showed `Temporarily unavailable` while local JANUS state remained intact. At the same time, GitHub email reported failures from legacy Phase 2/Phase 3 release workflows and clean-server proof jobs.

## Findings

- The Android client itself remained responsive and preserved local state during server unavailability.
- Phase 2 and Phase 3 release workflows are obsolete. They still reconstruct the retired legacy server and assert Android version 0.70, so they now generate false release failures against the native v1.08/recursive architecture.
- `server-v2-proof.yml` and `server-v2-diagnostic.yml` still wrote generated proof commits directly back to `main`. Concurrent proof/diagnostic jobs could race each other, generating non-fast-forward/push noise and unnecessary main commits.
- The live Render smoke workflow was stale: it only auto-ran for `render.yaml`, expected the old `consensus` route, and wrote results back to main. It therefore did not reliably verify current server changes.

## Recovery changes

- Remove obsolete Phase 2 and Phase 3 release checkpoint workflows.
- Make server-v2 proof and diagnostic workflows read-only; no CI-generated commits to main.
- Modernize live smoke to trigger for current `server_v2/**`, Render config, requirements, or the smoke workflow itself.
- Live smoke waits for Render deployment, requires `v2-clean-reconstruction` + `recursive-conscious-stream-v2`, verifies health/core count, registration/session auth, a real Chat response, local/global core sync, Stream Observe, and maintenance status, then attempts to delete the temporary CI account.
- Live smoke no longer asserts the retired `consensus` route and no longer writes docs commits back to main.

## Release rule

Treat the modern authoritative Android APK/RC1/recursive/conscious-stream/server-v2 workflows as release evidence. Historical Phase 2/3 workflow failures are not valid release blockers and must not be restored.

## Next verification

After merge, the updated live smoke must pass against `https://janus-global-core.onrender.com` before the real-device outage is considered resolved. Then retry Chat from the installed Android APK.
