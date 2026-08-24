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
Implemented and published:
- `JanusRoutePolicy` centralizes account-owned path policy;
- authenticated account-owned routes strip obsolete username/profile ownership hints while preserving operational filters;
- clearer Messages categories and unread emphasis;
- Reply in Chat / Mark read wording;
- clearer authentication/account continuity copy and destructive-action treatment;
- common loading/error copy improved.

## v0.88 — screen-state and high-level presentation extraction
Implemented on integration branch; release verification pending:
- new `JanusScreenStatePolish` moves another cohesive presentation responsibility out of `MainActivity`;
- loading/checking states become a consistent low-noise Working state;
- empty Messages state explains that JANUS only surfaces worthwhile interruptions;
- empty Observe state reinforces stable user-triggered snapshots and no auto-jump;
- common remote-failure states explain that local JANUS state remains intact;
- Messages is framed as a JANUS inbox rather than an internal telemetry dump;
- auth copy now frames sign-in as reconnecting device-local JANUS with global continuity;
- destructive account/session actions remain visually differentiated;
- New inbox cards, delivery status, Healthy, Reduced capability and Needs attention retain consistent semantic accents;
- v0.87 authenticated route hygiene and every earlier safe-area/Chat/Cores/Observe/product invariant remain gated in CI;
- no cognition, federation or server_v2 behavior changed.

## Next intended passes

1. Continue extracting feature-specific presentation and endpoint responsibility from `MainActivity` while preserving behavior.
2. Improve true Messages reply-context behavior, source/evidence cards, Memory filtering/search and Research presentation where server contracts allow it safely.
3. Consolidate repository continuity and CI after the Android UI settles.

Release rule: do not mark an Android pass fully released until the `apk-download` branch publishes the matching version after CI compilation and APK assembly.
