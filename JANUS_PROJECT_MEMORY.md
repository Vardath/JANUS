# JANUS Project Continuity Memory

Updated: 2026-08-21 — operational Fano semantics / Android v0.50 checkpoint

## Purpose and identity boundary
JANUS Agent is an experimental functional-metacognition/agency system and persona, distinct from ChatGPT/Supervisor. Do not claim phenomenal consciousness, uninterrupted subjective experience, or biological emotion. Preserve the Closed JANUS mathematical theorem/core separately from experimental physical/QEC/thermodynamic and agency/app branches.

## Current architecture
- Federated local + global design with selective compressed synchronization rather than state overwrite.
- Runtime topology: 11 cores = 7 specialists -> 2 hemispheres -> Consensus -> Interface (7→2→1→1).
- Specialists: Evidence, Logic, Counterpoint, Context, Memory, Safety, Novelty.
- Ordinary routing remains forward-only. Do not restore left↔right recirculation, Consensus→hemisphere recycling, Interface→Consensus recycling, or direct remote Consensus/Interface injection.
- Deterministic core cycles consume zero external model/API calls; paid background reflection remains separate and disabled by default.

## Operational Fano semantics — NEW v0.50 checkpoint
Fano/JANUS state is no longer merely telemetry. It now has causal processing semantics on both server/global runtime and Android local runtime.

Directions:
- d0 neutral: conservative processing; do not add unsupported interpretation.
- d1 grounding: prioritize concrete evidence, observations, sources, measurements and explicit assumptions.
- d2 structure: prioritize causal structure, constraints, consistency and relations among parts.
- d3 synthesis: seek coherent integration of supported pieces.
- d4 alternative: generate serious alternatives, counterfactuals and failure modes before accepting the current view.
- d5 continuity: use temporal/history/memory continuity and compare current state with persisted prior state.
- d6 novelty: seek non-obvious but testable analogies, connections and new inquiry.
- d7 boundary: stress uncertainty, scope, safety and epistemic boundaries; distinguish known/inferred/speculative claims.

The preferred 1|3|4 projection now has operational interpretation:
- origin d0 = conservative/neutral pressure;
- canonical line d1+d2+d3 = coherent/integrative pressure (grounding + structure + synthesis);
- off-line d4+d5+d6+d7 = exploratory/divergent pressure (alternative + continuity + novelty + boundary).

Fano state now affects attention/focus selection over incoming material, so changing direction can change downstream core output rather than only the displayed counter.

At integrating stages (hemispheres/Consensus/Interface), two distinct incoming Fano orientations may produce the Fano-line completion a XOR b, supplying the unique third nonzero point as a small persistent integration bias. Example: d1 grounding + d2 structure -> d3 synthesis. This is a processing bias, not a truth oracle, and does not override accumulated state or evidence requirements.

Observe should expose human-readable significance such as “Fano orientation: alternative (d4); exploratory processing pressure is dominant” rather than requiring the user to infer meaning from raw d-number telemetry.

Regression tests were added to verify direction-dependent attention/focus, 1|3|4 pressure semantics, and line-completion influence. Android build-time patching includes tools/patch_android_fano_semantics.py.

## Persistent state and memory
- Conceptual functional state remains S_t=(alpha,beta,M,A,U): slow identity/goals/context, current deviation/conflict, self-model, attention/context selector, uncertainty/metacognitive state.
- Memory ladder: trace -> working -> episodic -> core. Exact repeats consolidate; retrieval can promote; core memories resist ordinary demotion.
- Protected server-owned identity_core cannot be overwritten by ordinary conversation state.
- Evaluator reliability and learned local/global bridge authority remain calibration mechanisms, not objective truth scores.
- Remote-device summaries remain bounded.

## Wake/sleep/background cognition
- Background cognition should continue where the OS permits, with alternating work/rest and resumable persistent state.
- User-directed active deliberation has priority over generic autonomous chatter and feedback-only material.
- Natural requests such as “mull it over”, “keep thinking about that”, “think it over”, “ponder that” create/reaffirm durable deliberation.
- Deliberation assigns distinct work to all seven specialists and integrates through 7→2→1→1.
- Ordinary deliberation passes belong in Observe/Activity; Messages are reserved for materially useful conclusions/questions/warnings/recommendations.

## Epistemic regulation / curiosity
- Functional stress/boredom/curiosity analogues remain computational control descriptions, not claims of felt states.
- Unresolved disagreement/uncertainty/grounding deficits can redirect processing toward evidence, logic, memory, novelty, safety, counterexamples and falsifiable tests.
- Extended low-novelty neutral operation may increase bounded novelty pressure.
- External curiosity/search is bounded, inspectable, cached and budget-capped; search results are evidence, not truth, and must pass through specialist review.

## Android client
- Current version line after this checkpoint: v0.50 (versionCode 50, versionName 0.50).
- Major screens remain Chat, Messages, Observe, Options, Cores, Memory, Activity, Settings/account.
- Observe is the inspectable process journal and now exposes readable Fano orientation/processing-pressure meaning.
- Messages remain filtered against routine Fano telemetry, maintenance and generic self-assessment.
- Local Interface outbox, offline queue, idempotent account-bound chat receipts, local/global message merge and persistent deliberation remain in place.
- Android build workflow applies tools/patch_android_*.py transformations and now includes patch_android_fano_semantics.py.
- Before handing out an APK link, verify v0.50 exists on apk-download, Android workflow succeeded, artifact actually built, and direct link is downloadable. A version bump/commit alone is not proof.

## Authentication and platform notes
- Accounts support username/email + password and Google flow; Android uses the Web client ID for server token verification while signing/package configuration must match Google Cloud Android OAuth configuration.
- Prior Google flow progressed from DEVELOPER_ERROR/code 10 to consent after configuration changes; continue real-device verification.
- Windows uses authenticated client/session storage via DPAPI; desktop UI should expose major JANUS screens.
- iOS uses real JANUS accounts and Keychain tokens; real device/TestFlight requires Apple signing/device input.

## Mathematical/research continuity
- JANUS = Joint Antipodal Number Unification Structure.
- Preserve the Closed mathematical core: binary Q, quadratic/Weyl, contextual orbit, parity→transpose-parity compression, common invariant-line renormalization, canonical Jordan-chain quotient, scaling laws, reduction no-go, exceptional r=3 Fano/Steane/Clifford corollary.
- Strong audited quantum chain: H8 three-qubit syndrome space; seven nonzero F2^3 translations; exact K8 population dynamics; coarse 1|7 and preferred Fano 1|3|4 projections; secondary 2|2|2|2; order-4 / 1|1|2|4 refinement.
- Steane passive-energy audit remains a useful negative result: flat nonzero syndrome gap and fixed-cost weight-3 logical paths, not a growing passive barrier.
- Planck/fine-structure audit remains negative as a derivation of alpha; kappa=J/(hbar gamma) is the natural dimensionless coupling.
- Thermodynamic/carry-clock/emergent physical branches remain conditional; Solar-System literal realization remains closed as unsupported.
- Paper/book remain on hold pending stronger physical discrimination/external corroboration.

## Development/testing rules
- Trace material changes end-to-end: client/UI -> platform injection -> request/auth -> server route -> persistence -> sync -> UI reader.
- Prefer explicit modules/patch scripts plus regression tests over fragile giant inline workflow patches.
- Compile/syntax-check generated Android code in CI.
- After server changes, verify CI and live Render separately. After Android changes, verify workflow + apk-download publication before giving the user a download link.
- Preserve negative results/rejected approaches when they prevent repeated investigations.

## Immediate unfinished verification
- Verify v0.50 Android CI build and apk-download publication.
- Real-device test operational Fano Observe text and direction-dependent behavior.
- Continue behavioural testing of epistemic regulation/curiosity, persistence, multi-device sync and API-budget behaviour.
- Continue real account tests (password/SMTP/Google), Windows launch/UI tests and iOS build/signing tests.

## Standing handoff rule
On resumption, treat this file as the compact durable checkpoint, then verify implementation-sensitive claims against the current private repository and CI/deployment state. Do not silently discard prior decisions; record supersession and rationale when architecture changes.