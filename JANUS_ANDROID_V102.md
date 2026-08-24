# JANUS Android v1.02

## Scope
- Preserve full structured `JanusChatPresentation` data when a queued Chat turn is delivered after reconnect.
- Capture queued successful responses into `JanusChatResponseRegistry` so source cards and generated-image metadata remain available to the normal Chat renderers.
- Store queue replies in `offline_chat_replies_v2` with a serialized `presentation` object while draining the old v1 reply key once for compatibility.
- Delete the retired v1.00 reflective `JanusChatV2Surface` and `JanusChatHistoryBridge` classes. Direct v2 history ownership introduced in v1.01 remains authoritative.
- No server cognition, federation, auth ownership, topology, forward-routing, background-research or API-budget policy changes.

## Release gate
PR CI must pass the native boundary checks, structured queue assertions, Java compilation and APK assembly before merge. The `apk-download` branch must then publish v1.02 before the pass is considered released.
