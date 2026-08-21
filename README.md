# JANUS Global Core

JANUS is an experimental functional-metacognition/agency application with persistent local + global state. It does **not** claim phenomenal consciousness.

## Current architecture

Canonical cognitive topology: **11 cores arranged 7 → 2 → 1 → 1**.

- 7 specialists: Evidence, Logic, Counterpoint, Context, Memory, Safety, Novelty.
- 2 hemispheres: left synthesis and right synthesis.
- 1 Consensus core reconciles the hemispheres.
- 1 Interface core surfaces the result to Chat/Messages.

Ordinary routing is forward-only: specialists → assigned hemisphere → Consensus → Interface. Consensus/Interface output is not automatically recycled as a new topic. Remote/client summaries are compressed, tagged as feedback-only, and re-enter through specialist review rather than directly through Consensus.

## Current client status

- **Android v0.45** is the current published APK checkpoint. It includes forward-only routing, readable Observe output and tightened Messages filtering.
- **Windows v0.22** source/build workflow includes JANUS account login/register/session restore and DPAPI-protected session storage. Real Windows launch/use testing is still pending.
- **iOS** has authenticated account/session scaffolding, Keychain token storage and an unsigned simulator CI workflow. Apple signing/TestFlight/device testing is still pending.

This repository is still a development/beta project. Account creation/login, OAuth, email recovery, platform builds and long-running background behaviour should be tested before public release.

## Accounts and privacy

Private Chat, Messages, Observe, Cores, Memory, Activity and Settings routes are bound to the authenticated JANUS account rather than a client-supplied profile name. Passwords are stored only as salted PBKDF2 hashes. Server session tokens are stored as hashes; supported native clients use OS-protected token storage where implemented.

Public authentication endpoints are rate-limited. Detailed deployment/schema diagnostics require the server administrative token. Temporary chat-delivery receipts and repetitive runtime snapshots have bounded retention; meaningful conversation/memory continuity data remains until account deletion.

See `/privacy` and `/terms` on the deployed service for the current legal-development pages.

## API/background cost policy

Deterministic local/server core cycles do not require external language-model calls. Paid background language reflection is **disabled by default** in production. User-triggered Chat may use the configured OpenAI model. If paid background reflection is deliberately enabled later, per-profile daily call/token caps are already available.

## Render deployment

This repository includes a `render.yaml` Blueprint. Deployment uses the resilient `bootstrap:app` entrypoint. The historical base FastAPI module is reconstructed at build time from the checked-in `src/server.py.gz.b64.*` fragments via `tools/rebuild_server.py`; both Render and Docker use this same explicit step.

The Blueprint provides:

- one Starter web service;
- a 1 GB persistent disk mounted at `/data`;
- `JANUS_DB_PATH=/data/janus.sqlite3`;
- `/health` plus safe `/diagnostics/runtime-health` checks;
- automatic deployment from `main`;
- a generated `JANUS_ACCESS_TOKEN` for administrative endpoints.

Do not commit API keys, SMTP credentials, OAuth secrets, access tokens or private signing credentials.

## Reliability checks

GitHub Actions contains regression/build workflows for:

- Android APK builds and routing verification;
- authentication lifecycle/security tests;
- forward-only routing and remote-feedback tests;
- architecture/deployment contract checks;
- Windows client packaging;
- iOS simulator compilation.

Before treating a build as released, verify the actual artifact/download branch rather than inferring success from a version bump or commit alone.
