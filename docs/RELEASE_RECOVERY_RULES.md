# JANUS release recovery rules

1. Distinguish app-local health from remote-server health. Android may remain locally healthy while Render is unavailable.
2. Do not infer a product failure from historical Phase 2/3 CI. Those gates are retired.
3. Current server source verification and live deployment verification are separate requirements.
4. CI proof/diagnostic jobs must never mutate `main` with generated proof files.
5. After any `server_v2/**` production change, the live Android/server smoke test must verify Render health plus registration/auth, Chat, sync, Stream Observe and maintenance surfaces.
6. If live smoke fails, treat the deployment as unresolved even when local clean-server tests pass.
7. Do not erase local JANUS state in response to temporary remote unavailability.
