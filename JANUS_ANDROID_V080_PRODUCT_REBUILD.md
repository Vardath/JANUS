# JANUS Android v0.80 — faithful clean rebuild

## Product rule
v0.80 is not a new JANUS product. It is a brand-new Android implementation of the JANUS app already designed and tested. The user-facing structure, terminology and interaction model should remain recognisably JANUS while the implementation underneath is clean and maintainable.

## Canonical user experience
- Launch directly into JANUS, never a developer/control-panel home screen.
- Authentication surface: JANUS title, Sign in / Create account, password account flow and Continue with Google.
- Main shell: compact JANUS status header, then exactly four persistent primary tabs: Chat, Messages, Observe, Options.
- Chat is the default surface. It keeps the familiar You/JANUS bubbles, + attachment control, composer and Send button.
- Messages is JANUS's outbox for questions, observations, memories and follow-ups created outside the immediate turn.
- Observe is a readable journal/snapshot of externalizable 11-core activity. It must not expose private chain-of-thought or rapidly reset/refresh while the user is reading it.
- Options contains the deeper surfaces rather than placing them on the launch screen: cores, memory, activity, system status, artifacts, research workspace, maintenance review, background research/provenance, compatibility, settings and sign-out.
- Research, Artifacts, Maintenance and Settings may remain separate native activities internally, but are reached through Options so the app feels like one JANUS product.

## JANUS architecture preserved
The Android rebuild remains a client of the existing server-side JANUS architecture: 11 functional cores routed 7 specialists → 2 hemispheres → Consensus → Interface (7→2→1→1), persistent continuity/memory, governed background processing, research/web capability, attachments, artifact generation, and owner-gated maintenance. v0.80 must not replace this with fake local telemetry or a simplified persona.

## Mathematics / Fano boundary
The existing JANUS mathematical and Fano-derived structures remain part of the JANUS project/core where implemented. The Android UI should report or expose meaningful server-backed state; it must not invent mathematical effects simply to display the 1-3-7/Fano symbolism.

## Reliability rules
- No legacy patch/composer chain in v0.80.
- Native Android source is authoritative.
- Durable local Chat queue with stable client_message_id and bounded retry.
- Attachment uploads survive transient Chat failures through queued attachment IDs.
- One launcher only.
- Advanced features belong under Options, not on startup.
- Device validation is required before legacy retirement.

## Google sign-in
The native Google ID-token bridge remains implemented through /auth/google. Google error code 10 is treated as an OAuth package/signing-SHA configuration defect, not a reason to redesign JANUS. Password/account sign-in remains available while the v0.80 Android OAuth registration is corrected.

## Current reconstruction checkpoint
The diagnostic v0.80 Home screen has been retired. MainActivity is now the sole launcher and reconstructs the familiar JANUS shell: auth → Chat/Messages/Observe/Options, with Research/Artifacts/Maintenance/Settings moved back under Options. The next gate is CI compilation followed by real-device visual/functional validation and refinement against the previous JANUS app screenshots/behaviour.
