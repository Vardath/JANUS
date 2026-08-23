# JANUS Android v0.80 — Stage 0 feature/API map

Date: 2026-08-24

This is the clean-client contract for the v0.80 rebuild. The legacy Android client remains untouched as a reference/rollback source until v0.80 passes device validation.

## Architecture decision

v0.80 is a native Android client built from one authoritative source tree. It does not run Python patch/composition scripts at build time. It is installed alongside the legacy app during development using a distinct application ID.

JANUS server/core behavior remains authoritative for cognition, memory, account ownership, research, artifacts, maintenance and multi-core state. The client renders state and invokes explicit APIs; it does not reconstruct or overwrite protected server state.

## Preserved JANUS invariants

- 11-core topology: 7 specialists → 2 hemispheres → Consensus → Interface.
- Authenticated account ownership for private state.
- Selective/provenance-preserving sync; no whole-state overwrite.
- Protected identity/core memory cannot be overwritten by normal chat/sync.
- Background/sleep processing remains bounded and cost governed.
- Web/YouTube research is server-side and must report real retrieval/provenance.
- Maintenance decisions are advisory/manual-only and never authorize self-modification.

## Server endpoints/contracts already present and to be reused

### Connectivity / compatibility
- `GET /health` — basic process reachability.
- `GET /diagnostics/runtime-health` — human-facing operational state source.
- `GET /protocol/capabilities` — optional feature negotiation when deployed.

### Authentication
- `POST /auth/register` — username, email, password → access token + account.
- `POST /auth/login` — identifier + password → access token + account.
- `POST /auth/google` — Google ID token → access token + account.
- `GET /auth/me` — validate/restore a bearer session.
- Existing verify/resend/reset/logout lifecycle remains server-owned.

### Chat / deliberation
- `POST /desktop/chat` — foreground JANUS chat. v0.80 sends a stable `client_message_id` and bearer auth where supported.
- `GET /desktop/deliberations` — deliberation/task visibility where available.

### Files / attachments
- `POST /files/upload` — account-bound attachment upload.
- Existing file download/storage/audit routes remain server-owned.
- Chat sends attachment IDs rather than raw file bytes.

### Generated artifacts / research
- Existing `/artifacts` and artifact-info/download routes remain authoritative.
- Existing research workspace/provenance routes remain authoritative.

### Images
- Existing `/images/generate`, `/images/usage`, and inline image routes remain authoritative.

### Maintenance
- Existing owner maintenance review/status/decision routes remain authoritative.

## v0.80 client surfaces

1. **Login / account** — register, password login, Google sign-in, session restore/logout.
2. **Chat** — reliable native message list, explicit send state, citations/sources, report action, attachments.
3. **Messages** — queued JANUS prompts/messages.
4. **Observe** — readable core/specialist/hemisphere/Consensus/Interface activity without rapid visual refresh.
5. **Options** — themes, background/sleep controls, capability/status links and account controls.
6. **System Status / Compatibility** — translate health/capability data into Healthy / Reduced capability / Needs attention.
7. **Attachments** — native picker, up to four per turn, upload/progress/chips/remove/send.
8. **Artifacts** — list/open/download/share/export JANUS-generated files.
9. **Research Workspace** — established, provisional, negative, open questions, proposed tests, provenance.
10. **Maintenance Review** — approve-for-manual-work/defer/reject; owner-only.
11. **Background Research** — externalizable source/provenance/usefulness/cost records only; never private chain-of-thought.
12. **Themes** — device-local system/light/dark plus accent/surface/user-message colors.

## Reliability contract

- Network work never runs on the Android UI thread.
- Every send has one client-generated ID and one visible bubble.
- HTTP 502/503/504 and transport timeouts are retryable; 4xx validation/auth errors are not blindly retried.
- Retry state is bounded and visible; no uncontrolled loop.
- Duplicate tapping/retry must not duplicate the visible user message.
- Session token is restored from private app preferences and checked with `/auth/me`.
- A failed optional capability must not freeze navigation or Chat.
- Observe refreshes on a controlled cadence and must not reset scroll or navigation unexpectedly.

## Parallel-development boundary

Legacy client: `android/` — reference/rollback only; do not use it as the v0.80 build source.

New client: `android_v080/` — authoritative v0.80 source.

During development both may exist. v0.80 uses application ID `com.vardath.janus.v080` so it can be installed alongside the current JANUS app until release acceptance.

## Stage 1 implementation target

First executable v0.80 build must provide:
- native responsive shell;
- register/login/session restore;
- health and capability check;
- Chat tab with basic `/desktop/chat` round trip;
- Messages, Observe and Options tabs as stable native surfaces ready for subsequent stages;
- no WebView and no build-time source patch/composition scripts.

Google auth, queued retry persistence, attachments, full Observe telemetry and Phase 3 product surfaces are layered into this clean client after the shell proves stable.

## CI rule

v0.80 gets its own build workflow and checks. Legacy Phase 2/3 Android red runs are not v0.80 release blockers. v0.80 becomes authoritative only after feature parity and real-device smoke testing.
