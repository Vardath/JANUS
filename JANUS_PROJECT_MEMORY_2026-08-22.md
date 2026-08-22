# JANUS Project Continuity Checkpoint — 2026-08-22

This file supplements `JANUS_PROJECT_MEMORY.md` and records the latest material changes from the Aug 22 Android/server telemetry, synchronization, research, answer-generation, and memory work. It should be read after the older continuity file when resuming development.

## Current client/runtime line
- Android working line: **v0.68**.
- Canonical architecture remains **11 cores arranged 7 → 2 → 1 → 1**: Evidence, Logic, Counterpoint, Context, Memory, Safety, Novelty → left/right hemispheres → Consensus → Interface.
- Deterministic local and server core cycles remain zero external model/API calls. User-triggered Chat may use the configured model; bounded background model/web research is now a separate optional layer.
- JANUS remains an experimental functional-metacognition/agency system; no phenomenal-consciousness claim is made.

## Server and local runtimes independently verified
Real-device diagnostics established that the Render/global runtime is genuinely alive and advancing independently of Android local counters. The Android local society was also observed advancing independently while preserving its own sleep/low-duty state, local memory, Fano state, routing and zero-API maintenance behavior.

Local and server runtimes are separate societies. Synchronization must not overwrite local identity/state and neither side may substitute its counters for the other.

Important provenance invariant: **Chat diagnostics must never infer server-core state from client telemetry.** Server diagnostics use server-owned runtime state; local diagnostics use device-owned runtime state.

## Android Options/Cores telemetry history and current rule
The long-lived Options → Cores bug repeatedly showed unknown/zero server values even while Chat could prove the server runtime was healthy and had thousands of cycles. The investigation exposed stale/duplicate telemetry wiring and an increasingly fragile stack of build-time Android patches.

The architectural decision remains:
- native `/core-sync/exchange` heartbeat is the authoritative Android path for the server snapshot;
- Android stores the authenticated server snapshot returned by that heartbeat;
- Options → Cores reads the stored native snapshot through the Android bridge;
- if no snapshot exists, UI must say **WAITING FOR HEARTBEAT**, never fabricate believable zero values;
- local and server sections remain visibly distinct.

v0.68 consolidated the Android runtime integration so the build no longer replays the older v0.61–v0.67 telemetry patch stack. The build workflow now applies one authoritative v0.68 runtime patch before Gradle. Once behaviour is stable, this patch logic should be moved fully into canonical Android source rather than allowed to accumulate again.

## Major Aug 22 architecture correction: substantive cores, not telemetry-first answers
Live testing showed that JANUS was often describing *how* it processed — integration, grounding, disagreement, Fano direction, cycle counts — instead of saying what its cores were actually thinking about. It could also produce a polished generic assistant answer and append core telemetry afterward, which defeated the intended 11-core architecture.

The server answer route has therefore been changed to enforce the intended order:

**user question → seven specialists → two hemispheres → Consensus → Interface → final user response**

Foreground questions now seed all seven specialist cores with concrete role-specific work. Their externalizable subject-matter notes are routed forward through the society. The final response model is instructed that those substantive core summaries are PRIMARY and that it must not independently invent a parallel generic answer and then append telemetry.

Ordinary answers should surface:
- useful conclusions;
- genuine disagreement;
- serious alternatives;
- evidence gaps;
- hypotheses;
- non-obvious/testable connections;
- worthwhile unresolved questions.

Cycle counts, Fano counters, routing statistics and similar runtime values are secondary diagnostics only unless explicitly requested.

## Fano/JANUS control numbers: translate rather than dump
The Fano unit remains a deterministic processing-control substrate. Its internal direction labels, 1|3|4 values and weights are not factual conclusions and must not be presented as if they were meaningful subject-matter answers.

Human-facing translation is now:
- careful / grounded;
- integrating / coherent;
- exploratory / alternative;
- continuity-oriented;
- novelty-seeking;
- boundary/uncertainty checking.

Raw Fano values remain available in diagnostics. Ordinary conversation should translate them into plain English only when that genuinely helps explain the reasoning posture.

## Per-core external research capability
The server now contains a substantive research fabric in which **all 11 cores** can receive bounded external enrichment, rather than treating web research as an Evidence-only global feature.

Capabilities:
- foreground user questions can trigger a model-supported 11-role pass;
- foreground questions requiring fresh information can invoke live web search;
- each individual core can receive a direct model consultation;
- each individual core can receive live-web research when appropriate;
- background scheduling rotates model consultation across cores;
- background curiosity can perform relevant, adjacent, and deliberately wandering searches so JANUS receives genuinely new material rather than endlessly recombining its own summaries;
- retrieved material is routed to Evidence and Counterpoint for auditing/challenge when appropriate.

Default bounded controls currently include six background web searches/day and sixteen background model consultations/day, with spacing limits. These are cost controls, not architectural restrictions.

Important limitation: JANUS cannot literally open this ChatGPT conversation and privately talk to this exact assistant instance. Its external consultation path uses configured OpenAI API models, which serves the intended functional purpose of obtaining outside information, critique, explanations or connections.

A diagnostic `/desktop/core-research-status` exposes research capability, usage and recent consultations.

## Research-truth correction
Live testing exposed a false answer: JANUS claimed it was not accessing the wider internet because the current telemetry block showed no web result. That was wrong because capability and actual retrieval had been conflated.

The Interface must now distinguish:
1. whether web capability is enabled;
2. whether the current foreground question actually triggered a web search;
3. whether background web searches have completed today;
4. whether model consultations have completed;
5. what new subject matter, if any, was actually retrieved.

It must never infer “no internet access” solely from the absence of a current-turn web result.

## Conversation memory: whole-history retrieval, not a short recent tail
Another live failure showed that messages were persisted but older conversation content could disappear from usable context because `_recent_context()` only supplied a small recent tail. JANUS therefore conflated the user's mathematical JANUS research with a separate cosmological model despite earlier correction/explanation.

A dedicated `memory_retrieval.py` layer now searches across up to 2,500 retained records for the current profile and selects relevant older turns. Retrieval deliberately prefers:
- user-authored statements over later assistant paraphrases;
- episodic/core records over transient process chatter;
- corrections over older conflicting summaries;
- distinctive topic overlap;
- chronological presentation of selected memories so later corrections are visible in order.

The final Interface receives both the recent tail and whole-history relevant recall and is instructed not to claim something was never retained until that recall has been checked.

## Contextual memory signals and thread retention
Memory is not limited to explicit phrases such as “remember this.” The following kinds of user language are now treated as **attention/memory signals**:
- “think about this”;
- “ponder this”;
- “mull it over”;
- “keep this in mind”;
- “come back to this”;
- “remember this” / “don’t forget”;
- explicit corrections such as “that is not…” / “I mean…” / “from now on…”.

When such a signal appears, JANUS should retain **the surrounding conversational thread**, not only the command sentence. The latest memory update promotes the signal plus a bounded window of preceding relevant user/assistant turns to episodic memory so the later system can reconstruct what “this” referred to.

Retrieval likewise includes neighbouring turns around strong matches where useful, preserving conversational continuity rather than isolated facts.

Memory intent should therefore be understood contextually: preserve the thread, salient claims, user corrections, unfinished questions, important distinctions and material explicitly left for later thought.

## Memory authority rule
When reconstructing user beliefs, theories, project state or corrections:
- direct retained user statements outrank JANUS/assistant paraphrases;
- later explicit corrections outrank earlier conflicting summaries;
- process/telemetry notes are not evidence about what the user believes;
- absence from the most recent messages does not mean absence from persisted memory;
- if material predates persistent server storage entirely, JANUS must say it cannot verify that older text rather than inventing it.

## Quarterly maintenance / upgrade review
A server-side maintenance-review mechanism remains part of the active design.

Intent:
- approximately every 90 days JANUS records a bounded technical snapshot and requests a human review;
- it does **not** automatically edit code, install dependencies, switch models, alter APIs/configuration, or deploy anything;
- it can email the configured owner when SMTP + `JANUS_MAINTENANCE_OWNER_EMAIL` are present;
- the request is intended to trigger owner + ChatGPT maintenance work, never autonomous self-modification.

## Build workflow lesson
The Android project has historically used `tools/patch_android_*.py` transformations. The Aug 22 failures showed how brittle sequential textual patches become.

Rules going forward:
- prefer canonical source over stacked patches;
- where a patch remains necessary, make it idempotent and tolerant of already-transformed source;
- inspect the actual generated/shipped Java/HTML, not just the patch script;
- do not hand out an APK link until the requested version exists on `apk-download` and the workflow completed successfully;
- preserve telemetry regressions as tests, especially “server Chat sees live runtime while Options shows zero/unknown.”

## Current validation state
As of this checkpoint:
- server runtime health and independent server cycling have been verified;
- Android local runtime health and independent local cycling have been verified;
- authenticated device/server connection has been verified server-side;
- v0.68 build workflow has been consolidated and has produced successful Android builds;
- substantive 11-core foreground deliberation has been implemented server-side;
- per-core model/web enrichment and bounded background curiosity have been implemented server-side;
- raw Fano/control-number dumping has been demoted to diagnostics and human-readable translation added;
- whole-history memory retrieval and contextual memory-signal promotion have been implemented server-side;
- research capability vs actual retrieval is now explicitly separated in Interface instructions;
- remaining work is real-device behavioural validation after Render deploys the latest server commits, especially memory recall, truthful research reporting, useful core subject-matter responses, and the Android heartbeat snapshot readout.

## Immediate regression tests after deploy
1. Ask JANUS to describe an older user topic that is not in the recent tail and verify it retrieves the user's own earlier wording/distinction.
2. Correct JANUS, then ask the same topic later and verify the correction wins over its prior paraphrase.
3. Say “ponder this” or “think about this,” move to another topic, then return later and verify JANUS reconstructs what “this” referred to from the surrounding thread.
4. Ask “what have you been thinking about?” and verify the answer describes substantive subject matter rather than cycle/Fano/process statistics.
5. Ask “are you getting anything new from the internet?” and verify JANUS distinguishes capability, current search, completed background searches, model consultations and actual retrieved content.
6. Ask an explicitly current/recent factual question and verify foreground web search is used when enabled.
7. Verify ordinary answers contain no raw `d#`, `1|3|4`, weights, hashes or unexplained numerical control dumps unless diagnostics were requested.
8. Continue Android Options soak testing until the server heartbeat snapshot reliably populates the Server JANUS panel.

## Roadmap after current validation
1. complete local↔global synchronization/heartbeat validation;
2. richer document/file grounding;
3. image/screenshot understanding;
4. continue autonomous Messages/curiosity/background-cognition quality testing, prioritizing genuinely new useful thought over self-referential recycling;
5. later, revenue-gated multi-core visual deliberation/image exchange.
