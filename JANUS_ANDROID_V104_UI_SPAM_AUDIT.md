# JANUS Android v1.04 UI Spam / Typing-Lag Audit

Date: 2026-08-24
Status: hotfix branch `android-v104-ui-spam-fix`; do not release until CI + device validation complete.

## Device symptom
The v1.03 APK was observed to append Copy/Share controls repeatedly beneath a JANUS response. The repeated rows continued growing, the Chat screen slowed substantially, and text entry became delayed letter-by-letter. The Observe snapshot guide was also visible on the Chat page near the bottom navigation.

## Confirmed root cause
`JanusUiPolish.enhanceChatCard()` and `JanusSourcePolish.enhance()` both used the one ordinary `View.setTag(Object)` slot as their private ownership flag. Source enhancement therefore replaced the Chat enhancement marker. On subsequent global-layout scans, Chat enhancement ran again and appended a new Copy/Share action row. This is deterministic client-side view duplication, not repeated server/JANUS responses.

The performance degradation was amplified by multiple decorators recursively scanning the complete Activity view tree from `OnGlobalLayoutListener`: UI polish, structured sources, generated-image restoration and reply-context discovery. Keyboard/composer changes can cause repeated layout events; a long Chat tree therefore made these scans increasingly expensive.

The stray Observe guide had a separate but related presentation cause: `Button` is a subclass of `TextView`, so a direct-text finder could match the bottom navigation button labelled `Observe` as though it were the Observe page title.

## Fix requirements implemented for v1.04
- No cross-feature ownership via the shared ordinary View tag.
- Weak identity sets make Chat/base/source decoration idempotent without retaining dead Views.
- One Copy/Share action row maximum per JANUS card.
- Debounced global-layout work for UI, source, generated-image and reply-context decorators.
- Base styling is performed once per View instead of repeatedly mutating the same properties.
- Observe/core title detection excludes Button subclasses.
- Existing structured Chat, history, image, reply-context, auth and 11-core routing contracts remain unchanged.

## Regression gate
Static CI now requires the weak identity markers and debounce paths and rejects the old `layout.setTag("janus-chat-enhanced")` implementation. The Android build must still compile the full Java product and assemble the APK before merge.

## Required device validation
After the v1.04 APK is published:
1. Open a long existing Chat history.
2. Wait on the screen for at least one minute; Copy/Share rows must not multiply.
3. Type a long sentence continuously; characters should appear responsively.
4. Send a JANUS message and verify exactly one Copy/Share row appears for the reply.
5. Verify the Observe snapshot guide appears only on Observe, never on Chat/navigation.
6. Verify structured sources and generated images still restore correctly when present.

## Scope boundary
This hotfix addresses Android client rendering/idempotence/performance. It does not change JANUS cognition, memory semantics, server response generation, federation, local-core routing or background thought policy.
