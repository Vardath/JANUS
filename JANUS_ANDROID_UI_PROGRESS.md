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
Implemented and published: visible-memory search and tier filters, clearer Research evidence/category presentation, and clearer Account session/security actions.

## v0.90 — Messages reply-context extraction
Implemented and published:
- `JanusReplyContextPolish` converts the legacy visible quoted composer prefix into a separate native `Replying to JANUS` context card;
- the composer shows only the user's new text while typing;
- hidden quoted context is restored immediately before Send so the existing chat transport retains the same context;
- temporary reply context clears after send;
- no server/cognition/federation contract changed.

## v0.91 — Chat source-card presentation
Implemented on integration branch; release verification pending:
- new `JanusSourcePolish` extracts the current source appendix from rendered JANUS answers into a dedicated `Sources · N` panel;
- source title and domain are presented separately from the answer body;
- source rows with URLs are tappable and open through Android `ACTION_VIEW`;
- answer text no longer displays the raw appended `Sources:` block;
- source rendering is isolated from network/cognition logic and preserves the existing server response contract;
- this is a compatibility presentation bridge: MainActivity still flattens the structured server source array before render, and a later transport refactor can pass the raw source objects directly;
- the Android workflow is consolidated to reduce brittle historical literal-string checks while retaining native-boundary, safe-inset, reply-context, source-card, route-hygiene, 11-core architecture, Java compile, APK assemble and publication checks.

## Next intended passes

1. Move raw source metadata and reply context into explicit Chat presentation models so the renderer no longer needs compatibility parsing.
2. Continue extracting endpoint/feature responsibilities from `MainActivity` into dedicated native surfaces/controllers.
3. Improve wider-screen/tablet responsiveness and remaining accessibility/details after the core product surfaces are separated.

Release rule: do not mark an Android pass fully released until the `apk-download` branch publishes the matching version after CI compilation and APK assembly.
