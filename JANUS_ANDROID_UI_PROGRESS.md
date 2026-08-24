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
Implemented and published: `JanusScreenStatePolish` extracted consistent loading, empty, failure, inbox and account/session state presentation from `MainActivity`; CI assertion corrected and matching APK published.

## v0.89 — Memory / Research / Account feature extraction
Implemented and published:
- `JanusFeaturePolish` contains feature-specific presentation behavior without networking or cognition logic;
- Memory has client-side visible-memory search and All / Trace / Working / Episodic / Core filters;
- Research evidence counts and epistemic categories are clearer;
- Account has a dedicated Session & security section and clearer per-device/all-device sign-out actions.

## v0.90 — Messages reply-context extraction
Implemented on main; release verification pending:
- new `JanusReplyContextPolish` converts the legacy visible `Regarding your message:` composer prefix into a separate native `Replying to JANUS` context card;
- the composer contains only the user's new reply while they type;
- immediately before Send, the hidden quoted context is restored to the outgoing composer payload so the existing `/desktop/chat` transport receives the same contextual message as before;
- after the send clears the composer, the temporary reply-context state/card is cleared;
- no server, cognition, federation or message-state contract changed;
- CI now requires the reply-context bridge and all earlier UI/runtime/security invariants before v0.90 can publish.

## Next intended passes

1. Replace the compatibility bridge with explicit reply-context payload fields if/when `server_v2` gains a first-class reply-context contract.
2. Add richer Chat source/evidence cards from structured source metadata rather than appended plain source text.
3. Continue moving endpoint and feature responsibilities out of `MainActivity`, then consolidate repository continuity/CI once the Android product UI settles.

Release rule: do not mark an Android pass fully released until the `apk-download` branch publishes the matching version after CI compilation and APK assembly.
