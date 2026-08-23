# JANUS Android v0.80 feature-parity audit

Status: active rebuild baseline after UI consolidation and Google-auth restoration.

## Preserved server/core invariants

- Same JANUS server/global core; Android v0.80 is a client rewrite, not a new cognition system.
- 11-core topology preserved: 7 specialists → 2 hemispheres → Consensus → Interface.
- Persistent account identity, continuity, memory, selective local/global synchronization and protected identity boundaries remain server-owned.
- Existing live-web/YouTube research, attachment grounding, artifact creation, provenance, maintenance review and image-generation services remain server-side contracts.
- Fano/JANUS mathematical research is preserved in the project/research layer; the Android client does not replace or reinterpret the mathematical core.

## v0.80 implemented parity

- Native account registration/login and session restore.
- Native Google sign-in bridge: Google ID token acquisition on Android, server-side verification through `/auth/google`, then the same account-bound JANUS access token/session used by password login.
- Resilient Chat with durable local queue, client_message_id deduplication and bounded 8/25/60 second retry.
- Native Messages view for JANUS proactive outbox.
- Stable Observe snapshot for runtime/core telemetry without rapid-refresh scroll disruption.
- Human-readable System Status: Healthy / Reduced capability / Needs attention.
- Native file picker and authenticated uploads, four attachments per Chat turn, removable attachment chips, queue-persistent attachment IDs and server grounding/vision integration.
- Native Artifacts workspace: continuity report, research digest, working note; authenticated download; Android open/share/export through FileProvider.
- Native Research workspace: retrieved evidence, provisional hypotheses, negative results, open questions, proposed tests, provenance/background-research records and research-digest creation.
- Native maintenance owner review: approve for manual work / defer / reject, with no autonomous self-modification or deployment.
- Client-local theme mode, accent colours, background-cycle controls, Observe telemetry control and local cadence.
- Protocol/capability and runtime-health checks.
- Single v0.80 launcher (`HomeActivity`) providing one coherent JANUS entry point. Feature screens are internal activities, not separate launcher icons.

## Google sign-in validation note

The clean v0.80 client now contains the Google sign-in implementation and uses the JANUS web OAuth client ID to request an ID token for server verification. The development package is `com.vardath.janus.v080`, intentionally separate from the legacy app so both can coexist during validation. Google/Play Services may still require the Android OAuth configuration for this development package/signing certificate before on-device sign-in succeeds. That is a deployment-console validation item, not a reason to reintroduce the legacy patch chain.

## Still to verify before v0.80 replaces legacy Android

- CI build green on the current consolidated/Google-auth commit.
- Real-device launch responsiveness and tab/navigation responsiveness.
- Existing-account password sign-in and session restoration on device.
- Google sign-in on device; if Google reports a developer configuration error, register/verify the v0.80 package + signing SHA in the existing Google project, then retest.
- Chat round trip against live Render service, including a live-web/YouTube research request.
- Offline/transient-failure queue and recovery on real device.
- Messages load and stable Observe scroll behavior.
- Attachment tests: text/PDF/image; four-file limit; grounded response; transient retry with attachments.
- Artifact create → download → open/share/export on device.
- Research provenance rendering against live account data.
- Maintenance screen behavior for owner account and graceful non-owner handling.
- Theme/background preference persistence across process restart.
- Final navigation polish may move internal activities into fragments/screens later, but that is not required for functional parity if the single-launcher flow is coherent and reliable.

## Legacy retirement gate

Do not delete or archive the legacy Android client until all of the following are true:

1. v0.80 CI/release gate is green.
2. A known-good APK is installed and exercised on the real Android device.
3. Auth, Chat, live research, Messages, Observe, attachments, artifacts, research, maintenance and options all pass representative smoke tests.
4. Google sign-in succeeds on the real device or is explicitly deferred by owner decision after the implementation has been validated as far as possible.
5. No critical legacy-only feature remains undocumented.

After the gate passes, archive the old composer/patch Android pipeline under legacy/reference status and make v0.80 the authoritative Android product.
