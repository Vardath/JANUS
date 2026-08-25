# JANUS recovery summary — 2026-08-25

The installed Android app preserved local state correctly during a temporary remote outage, but foreground Chat could not reach the live server.

Repository investigation found two independent issues:

1. stale historical CI (Phase 2/3) was guaranteed to fail against the current native v1.08 recursive product;
2. proof/diagnostic workflows still committed generated status files back to `main`, allowing concurrent jobs to race and create misleading failure notifications.

The recovery branch removes those obsolete gates, makes proof/diagnostic CI read-only, and upgrades the live production smoke test to the current recursive server and Android-critical path. The live smoke is the authoritative external check for resolution of the observed outage.
