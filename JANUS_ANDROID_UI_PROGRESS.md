# JANUS Android UI Improvement Progress

Updated: 2026-08-24

## Authoritative baseline

- Android product: native `android/` client only; no WebView/generated HTML/patch-composer product path.
- Production server: `server_v2/`.
- Runtime topology remains 7 specialists -> 2 hemispheres -> Consensus -> Interface.
- Preserve forward-only routing, feedback-only federation, stable Observe snapshots, zero-API deterministic local cycles, authenticated account ownership, and owner-gated maintenance.

## v0.83 — safe areas and native chrome
Implemented and published: system/status/navigation/IME insets, theme-aware system bars, rounded native controls, app-wide dynamic-screen polish.

## v0.84 — Chat readability/actions
Implemented and published: selectable responses, Copy/Share/Report, delivery-status cards, improved attachment/image treatment, tappable links and long-response spacing.

## v0.85 — Cores and Observe architecture presentation
Implemented and published: native 7 -> 2 -> 1 -> 1 architecture map, Local/Global distinction, human-readable Fano orientations, stable non-auto-jumping Observe snapshots.

## v0.86 — product-surface readability
Implemented and published: clearer Options hub, Memory tiers, Research headings, semantic System Status, background cadence labels, owner-gated Maintenance explanation.

## v0.87 — Messages/Auth usability + authenticated route hygiene
Implemented and published: centralized account-owned path policy, bearer-token ownership hygiene, clearer Messages categories, Reply in Chat / Mark read wording, cleaner auth/account continuity and common loading/error copy.

## v0.88 — screen-state and high-level presentation extraction
Implemented and published:
- `JanusScreenStatePolish` extracted consistent loading, empty, failure, inbox and account/session state presentation from `MainActivity`;
- stable Observe and local-state-preserving failure wording retained;
- CI gate corrected after a case-sensitive assertion error and the matching v0.88 APK was published.

## v0.89 — Memory / Research / Account feature extraction
Implemented on integration branch; release verification pending:
- new `JanusFeaturePolish` contains feature-specific behavior with no networking or cognition logic;
- Memory now gets client-side search across visible loaded memories;
- Memory tier chips filter All / Trace / Working / Episodic / Core without another server request;
- filter logic only hides recognized memory cards, preserving section/navigation structure;
- Research evidence counts become compact human-readable evidence badges;
- Research epistemic categories receive differentiated card accents while retaining established/hypothesis/negative/open/proposed separation;
- Account gains a clearer `Session & security` section when session lifecycle actions are present;
- sign-out controls distinguish `Sign out this device` from `Sign out all devices`;
- v0.89 CI gates the new Memory filtering, Research evidence and Account/session behavior plus all prior Android invariants;
- Messages reply transport is intentionally unchanged because the current implementation embeds quoted context in the composer; this will be changed only when reply context can remain in the sent payload without merely hiding it visually.

## Next intended passes

1. Extract true Messages reply-context state/payload so the surfaced message can appear as a quote card without dumping up to 500 characters into the composer.
2. Add richer source/evidence presentation where server responses expose enough metadata safely.
3. Continue moving endpoint and feature responsibilities out of `MainActivity`, then consolidate repository continuity/CI once the Android product UI settles.

Release rule: do not mark an Android pass fully released until the `apk-download` branch publishes the matching version after CI compilation and APK assembly.
