# JANUS route/security inventory

Phase 2 Step 2. This inventory classifies the externally reachable server surfaces by the identity boundary that is allowed to select data. The governing rule is simple: a client-supplied `username` or `profile_id` is never authorization.

## Public by design

These routes expose no private account content and are intentionally usable before a session exists:

- authentication bootstrap/lifecycle routes that must exist before login, such as registration/login/Google authentication and verification/reset entry points;
- public legal documents such as privacy policy and terms of service;
- `/health` and `/diagnostics/runtime-health`, which expose bounded operational health only;
- `/diagnostics/auth-config`, which exposes configuration/route-presence booleans rather than account data or secrets.

## Administrator-token boundary

Detailed deployment diagnostics are not account APIs. They require the server-admin token enforced by `bootstrap._require_admin()`:

- `/diagnostics/auth-detail`;
- `/diagnostics/maintenance`;
- `/diagnostics/maintenance/run`;
- `/diagnostics/startup-error` when the bootstrap is degraded.

The public runtime/auth-config diagnostics must remain less detailed than these admin routes.

## Account-session-bound routers

These modules perform their own authenticated-account lookup and derive the profile/account partition from the session rather than a selector supplied by the client:

- `/core-sync/*` — authenticated account/device presence and selective federated exchange;
- `/files/*` — account-bound file upload/list/read/download/delete/storage operations;
- `/artifacts/*` — account-bound generated working artifacts;
- `/images/generate`, `/images/usage`, `/images/{file_id}/inline` — authenticated generation, usage and image retrieval;
- `/research/*` — research workspace and evidence records;
- `/reliability/*` — account-scoped reliability audit/history;
- authenticated account lifecycle/deletion/report routes where the router already resolves the account from the session.

## Desktop/private routes secured by `secure_desktop`

The legacy desktop surface historically used `username` query arguments internally. `secure_desktop.install()` now captures those implementations, removes the externally reachable originals and re-exposes session-bound wrappers. Compatibility implementations may retain a username parameter internally, but the externally reachable wrapper supplies only the authenticated username.

Session-bound routes include:

- `POST /desktop/chat`;
- `GET /desktop/observe`;
- `GET /desktop/core-observe`;
- `GET /desktop/cores`;
- `GET /desktop/memory`;
- `GET /desktop/activity`;
- `GET /desktop/settings`;
- `GET /desktop/home`;
- `GET /desktop/messages`;
- `POST /desktop/messages/{event_id}/state`;
- `GET /desktop/runtime-cores`;
- `GET /desktop/deliberations`;
- `GET|POST /desktop/continuity`;
- `POST /desktop/continuity/{item_id}/state`;
- `GET /desktop/continuity/{item_id}/events`;
- `GET /desktop/hive-budget`;
- `GET /desktop/core-research-status`;
- `GET /desktop/message-quality`;
- `GET /desktop/self-assessment`.

For write routes, a copied payload has `profile_id` and `username` replaced with the authenticated username before the legacy implementation receives it. `_janus_token` is removed from the forwarded payload.

## Late-installed desktop routes

Some features are installed by `bootstrap.py` after `secure_desktop` has already run. These must authenticate internally rather than relying on the earlier wrapper pass.

- `/desktop/cost-status` authenticates through `secure_desktop._profile()` and has no username selector;
- `/desktop/message-thread` and `/desktop/message-thread-status` authenticate through `auth.require_account()` and have no username selector.

Unknown legacy username query parameters sent by older clients may still arrive, but FastAPI ignores them because they are no longer part of the route signature; they therefore cannot select another partition.

## Cross-account invariants

1. Authentication is resolved before profile-scoped reads, writes, thread lookup, research grounding, cost accounting or lifecycle changes.
2. Account-bound resources use the authenticated numeric account id where the schema provides one.
3. Profile-bound legacy resources use the username obtained from the authenticated account.
4. A forged `username`/`profile_id` in query or payload cannot redirect a request into another account's data.
5. Public diagnostics expose operational booleans only; detailed deployment information is admin-token-bound.
6. Global 11-core operational summaries may be shared where explicitly designed, but profile-specific observations, memories, research, messages, continuity and budgets remain session-bound.
7. Selective local/global synchronization derives the server profile from the authenticated account and never trusts a device-supplied profile identity.

## Regression coverage

`tests/test_profile_boundary_hardening.py` protects the post-security chat normalization, cost-status signature, remaining desktop profile wrappers, late-installed proactive-thread authentication, and the declared private-route inventory. Additional auth and selective-sync suites continue to cover account isolation at their own protocol boundaries.
