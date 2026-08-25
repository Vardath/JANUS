# Current JANUS release gates

Authoritative current gates:

- Build JANUS Android APK
- Test JANUS Android RC1 readiness
- Test JANUS Recursive Core Engine
- Test JANUS Conscious Stream Cycle
- Test clean JANUS server v2
- Prove clean JANUS server v2
- Diagnose clean JANUS server v2
- Test JANUS Protocol Capabilities
- Test JANUS Android UI Hardening
- Test JANUS Android Localization
- Test JANUS Android Maintenance Review
- Test JANUS Maintenance Request Ledger
- Smoke test live JANUS Android/server path

Obsolete historical Phase 2 / Phase 3 release workflows were removed on 2026-08-25. They asserted retired legacy-server composition and Android v0.70 and must not be used to judge current v1.08 recursive JANUS release readiness.

CI proof/diagnostic workflows are read-only. They must not push generated status commits back to `main`; this avoids workflow races and false failure email noise.
