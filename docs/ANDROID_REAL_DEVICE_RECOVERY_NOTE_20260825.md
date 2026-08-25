# Android real-device recovery note — 2026-08-25

Observed on installed Android v1.08 during release soak:

- Chat UI remained available.
- Local JANUS state remained intact.
- Foreground Chat attempts returned `Temporarily unavailable` while the remote connection was unavailable.
- This behavior confirms graceful local-state preservation, but not server availability.

The corresponding GitHub failure-email burst included obsolete Phase 2/3 workflows and self-writing proof jobs; those are being removed/hardened separately from the real Render availability check.

Resolution requires the modern live Android/server smoke workflow to pass against the deployed Render service, followed by a successful real-device Chat retry.
