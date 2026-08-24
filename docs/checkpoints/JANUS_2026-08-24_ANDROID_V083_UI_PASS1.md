# JANUS Android v0.83 UI improvement pass 1 — 2026-08-24

## Authoritative baseline

This pass continues from the clean reconstruction baseline: native `android/` client + clean `server_v2/`. The old Android WebView/HTML/patch/composer lineage and old composed server wrapper lineage remain historical reference only and must not be revived.

## Scope completed in this pass

- Added app-wide system-bar safe-area handling so JANUS content sits below the Android status area and above Android navigation/gesture controls.
- Added IME/keyboard inset handling using the larger of bottom system-bar and keyboard insets, with `adjustResize` retained as a platform fallback.
- Added transparent system/navigation bars with light/dark icon contrast matched to the current JANUS theme.
- Added an application-level native UI polish layer that automatically restyles dynamically-created programmatic views without changing the working Chat/auth/runtime behavior.
- Navigation buttons now receive clearer selected/unselected treatment and minimum touch height.
- Generic native buttons receive consistent sizing, casing, spacing and surface treatment.
- Text inputs receive rounded elevated surfaces, borders, readable hint/text colours and consistent minimum touch height.
- Existing JANUS cards and user chat surfaces receive rounded corners/elevation while preserving existing semantic colours.
- Text containing web URLs becomes tappable and line spacing is slightly increased for readability.
- The polish layer is registered through `JanusApplication`, so screens rebuilt dynamically after navigation continue to receive the same visual treatment.
- Android version advanced from 0.82 to 0.83.
- Android CI now explicitly checks the safe-area/IME/UI-polish contract before compiling the real app.

## Intentionally unchanged

- 7 specialist -> 2 hemisphere -> Consensus -> Interface routing.
- Device/global selective-no-overwrite federation.
- Authentication/account ownership.
- Offline queue and chat idempotency.
- Stable Observe snapshot behavior.
- Research, files, images, artifacts, maintenance and server_v2 API behavior.
- Background deterministic zero-model-call policy.

## Next passes

1. Chat presentation: richer response cards, source cards, message actions, attachment/image treatment and better send/queue state.
2. Runtime Cores / Observe: human-readable Fano orientation, visual 7->2->1->1 map and clearer local/global comparison.
3. Messages / Options / Memory / Research / System / Maintenance visual hierarchy and reusable screen components.
4. Progressive separation of the large MainActivity into focused native components/repositories without another product rewrite.
5. Continuity/CI cleanup marking superseded legacy instructions unmistakably as historical.

## Verification rule

This checkpoint is not release acceptance by itself. The current-head Android workflow must pass static invariants, Java compilation and APK assembly. Real-device acceptance must additionally verify status/navigation bar clearance, gesture/button navigation clearance and composer behavior with the keyboard open.
