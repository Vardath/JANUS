# JANUS Android v0.84 Chat polish checkpoint

This pass builds on the verified v0.83 native/safe-area baseline and deliberately leaves the 11-core local runtime, server_v2 cognition path, account/auth ownership, offline queue and federation contracts unchanged.

## Scope

- Richer JANUS/user/system message-card styling via the app-wide native polish layer.
- Compact attachment chips and clearer composer controls.
- Tappable web links and improved long-response readability.
- Automatic Copy and Share actions on JANUS message cards, while retaining the existing Report response action.
- Cleaner treatment of offline/system delivery messages.
- Framed generated-image presentation.
- No WebView, generated HTML or legacy patch/composer pipeline.

## Verification rule

The Android release workflow must compile Java, assemble the APK, preserve all existing product/server contract checks and verify the new chat-polish markers before publishing v0.84 to the apk-download branch.
