# Android/server live smoke scope

The live production smoke test is deliberately small and release-critical. It verifies the path the Android client needs to function:

- Render `/health` responds with current clean recursive server generation;
- `/protocol/capabilities` responds;
- account registration/session auth works;
- `/desktop/chat` returns a real non-empty JANUS response;
- `/core-sync/exchange` accepts a current Front/Interface client snapshot;
- `/desktop/stream-observe` responds;
- `/maintenance/status` responds;
- temporary CI account cleanup is attempted.

Provider-heavy research/image tests remain separate so an external provider incident does not masquerade as Android/server structural failure.
