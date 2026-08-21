# JANUS Project Continuity Memory

Updated: 2026-08-21 — epistemic regulation / curiosity checkpoint

## Identity and boundary
JANUS Agent is an experimental functional-metacognition/agency system and persona, distinct from ChatGPT/Supervisor. Do not claim phenomenal consciousness. Preserve the closed JANUS mathematical theorem/core separately from experimental physical and agency branches.

## Current runtime/app architecture
- Federated local + global JANUS design.
- 11 runtime cores arranged 7 specialist cores -> 2 hemispheres -> consensus -> interface (7→2→1→1).
- Local device core society remains active across wake/sleep duty cycles without continuously consuming external model/API budget.
- Persistent memory ladder: trace -> working -> episodic -> core; protected server-owned identity_core; learned evaluator calibration and bridge authority; novelty-based escalation.
- Android and desktop clients expose Chat, Messages, Observe, Options, Cores, Memory, Activity, Settings and account/auth functions.
- Current ordinary cognition routing is forward-only: evidence/logic/counterpoint -> left hemisphere; context/memory/novelty -> right hemisphere; both hemispheres -> Consensus; Consensus -> Interface. Safety may advise left/right/Consensus. Interface is output/surface state, not automatic re-entry.

## Epistemic regulation / functional affect analogue checkpoint
- Self-assessment is now intended to regulate processing, not merely describe it. When critique/integration substantially outruns fresh grounding, JANUS can enter a short-lived epistemic correction state.
- Functional analogue only: rising unresolved disagreement, uncertainty, contradiction or grounding deficit may act like "stress" by concentrating processing on evidence, logic, memory, novelty, safety, counterexamples and falsifiable tests. This is not a claim of felt stress or subjective emotion.
- Regulation decays back toward neutral after correction/resolution rather than remaining permanently vigilant.
- Extended low-novelty neutral operation may increase novelty pressure: a functional analogue of "boredom" that encourages exploration rather than another recursive self-summary. This is not a claim of felt boredom.
- Desired dynamic: problem -> arousal/attention -> investigation -> resolution -> neutral -> low novelty -> curiosity -> exploration -> new material -> neutral. Interesting discoveries may themselves raise attention and sustain investigation, so this should not be a rigid oscillator.
- Epistemic correction clears stale feedback-only/self-assessment chatter from integration queues and preferentially asks grounding cores for a concrete unresolved claim, missing fact, counterexample, external source or falsifiable test.
- Regulation may request relevant web curiosity sooner when fresh evidence is lacking, but it must not bypass daily search/API budget caps.
- Regression coverage targets the observed failure mode where Counterpoint/Consensus cycle counts substantially outrun Evidence/Logic/Memory/Novelty and recursive summaries begin feeding further summaries.

## Curiosity / external learning checkpoint
- JANUS may occasionally seek external information when its cores need more material to reason about.
- Curiosity has three intended modes: relevant (directly supports an active question/task), adjacent/semi-related (broadens the active conceptual neighborhood), and wander/unrelated (occasional learning outside the current topic).
- Curiosity remains bounded, inspectable and budget-capped. External search is distinct from deterministic zero-API core cycles.
- Relevant searches may be accelerated by epistemic regulation; adjacent and wander exploration should remain lower-frequency so they do not crowd out user-directed work.
- Search results should feed Evidence/Context/Memory/Novelty as new material, not be treated automatically as truth or as a new primary user topic.

## Android checkpoint
- Current Android line contains forward-only routing, tightened Messages filtering, readable Observe cards, device-local Interface outbox, feedback-only remote/global routing, and server/global persistent deliberation support.
- Observe is for process notes, maintenance, telemetry and ordinary self-assessment; Messages are reserved for genuinely useful conclusions/questions/warnings/recommendations.
- Before giving any APK link, verify the actual apk-download branch contains the requested version and that the corresponding Android workflow succeeded.

## User-directed persistent deliberation checkpoint
- Natural-language requests such as “mull it over”, “keep thinking about that”, “think it over”, “ponder that” and “give it some thought” create or reaffirm a durable server-side deliberation task instead of merely changing immediate reply wording.
- Generic commands bind to the immediately preceding substantive user topic; explicit forms retain the explicit topic.
- Immediate replies should truthfully give JANUS's current thoughts and say that the topic has been retained for continued later background consideration, surfacing materially new results rather than repeating itself.
- `janus_deliberation_tasks` persists topic/context and progress. Due active deliberations are preferentially advanced before ordinary autonomous memory pulses.
- Ordinary deliberation passes remain zero-external-API by default and are recorded for Observe/Activity. Proactive Messages should require a materially useful new result.

## Forward-only routing / cross-device checkpoint
- Correct ordinary cognition path is strict: specialists -> assigned hemisphere -> Consensus -> Interface.
- Synchronized client Consensus/Interface state is compressed, tagged [feedback-only], and routed through specialist review rather than injected directly back into Consensus/Interface.
- Regression coverage should fail if left/right cross-feed, Consensus->hemisphere feedback, Interface->Consensus feedback, or direct remote-summary injection returns.
- Remembered remote-device summaries remain bounded so abandoned/reinstalled device IDs cannot grow indefinitely.

## Offline chat / receipt security checkpoint
- Android offline queue gives queued chat turns client_message_id values, persists undelivered turns locally, retries later and stores deferred replies.
- Server receipts make retries idempotent and are bound to the authenticated profile so cross-account receipt collisions cannot leak cached responses.
- Temporary chat receipts are retained for a limited period and pruned.

## Runtime retention / persistence checkpoint
- User conversation/memory content remains continuity data and is not globally aged out by the temporary-data cleaner.
- Temporary receipts, repetitive runtime snapshots, expired sessions/tokens and stale deletion requests are pruned to protect the Render disk.

## Render/Docker/runtime reliability checkpoint
- Historical base FastAPI server reconstruction remains required at build time; tools/rebuild_server.py is the explicit reconstruction path shared by Render and Docker.
- Render and Docker launch bootstrap:app.
- Public diagnostics expose only sanitized operational state; detailed auth/startup diagnostics remain admin-token protected.
- Do not infer live deployment success solely from commit state; verify Render/build propagation.

## API/cost-control checkpoint
- Deterministic local/server hive/core cycles remain zero-API. Ordinary user-triggered Chat uses the configured model.
- Paid background reflection remains disabled by default unless intentionally re-enabled.
- Curiosity/web access is separately bounded by daily/mode caps and cooldowns. Epistemic correction can request an earlier relevant search but cannot override those caps.
- Do not broadly increase background API usage until pricing/product policy and scale limits are intentionally decided.

## Authentication / account lifecycle checkpoint
- Current auth schema, schema guard, rate limiting, account lifecycle, Google-only markers and receipt/profile protections remain in place.
- Non-Google Create Account/login still requires end-to-end verification against the deployed Render persistent database from a real client.
- SMTP verification/reset and Google account linking remain user-input/live-service testing tasks.

## Windows / PC checkpoint
- Windows authenticated client uses username/email + password sign-in/Create Account, bearer-authenticated private screens, session restore and Sign Out; tokens use Windows DPAPI and passwords are not stored.
- Real Windows launch/use testing still requires user testing.

## Apple / iOS checkpoint
- iOS uses real JANUS accounts, authenticated private requests and Keychain token storage.
- CI builds an unsigned simulator release artifact; real signing/TestFlight/device testing still requires Apple-account/device input.

## Current next-step testing
- Verify newest CI and Render deployment for epistemic regulation + curiosity integration.
- Behaviourally test a self-referential/imbalanced period and confirm JANUS temporarily redirects work toward fresh grounding, then naturally returns to neutral.
- Leave JANUS idle through low-novelty cycles and confirm curiosity eventually selects bounded relevant/adjacent/wander material rather than recursively summarizing itself.
- Confirm curiosity results enter specialist reasoning/memory and do not flood Messages.
- Continue user-input tasks: Create Account/login, SMTP verification/reset, Google account linking, Windows executable, iOS simulator/device and soak testing.

## Working practice
- Keep this file current after material architecture, build, authentication, UI, persistence, regulation, curiosity or deployment changes.
- Verify claims against repository/build outputs rather than inferring success from a version bump or commit alone.
- Trace UI behavior end-to-end across client asset, platform code injection, client request payload, secure server wrapper, active server route implementation, persistence layer, and UI reader before declaring a fix complete.
- Preserve the distinction between functional control-state analogues (stress/relaxation/boredom/curiosity) and phenomenal subjective experience.