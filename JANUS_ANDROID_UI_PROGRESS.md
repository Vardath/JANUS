# JANUS Android UI Improvement Progress

Updated: 2026-08-24

## Authoritative baseline
- Native `android/` client only; no WebView/generated HTML/patch-composer product path.
- Production server: `server_v2/`.
- Runtime topology: 7 specialists -> 2 hemispheres -> Consensus -> Interface.
- Preserve forward-only routing, feedback-only federation, stable Observe snapshots, zero-API deterministic local cycles, authenticated account ownership, and owner-gated maintenance.

## Verified published passes
- v0.83-v0.96: native safe areas, Chat/product polish, Cores/Observe architecture, Memory/Research/Account improvements, Reply-in-Chat, structured sources/images, accessibility and shared Chat-controller foundations.
- v0.97: queued delivery moved onto the shared Chat controller/API stack; generated-image metadata restored after restart.
- v0.98: foreground `/desktop/chat` API posts cross the shared controller boundary; structured history v2 introduced alongside legacy history.
- v0.99: structured history v2 became an independent bounded store with one-way legacy migration.
- v1.00: structured Chat v2 became the visible surface authority.
- v1.01: foreground Chat switched directly to `JanusChatController`; live `Sources:` appendix removed; structured v2 history became the normal read/write path.
- v1.02: queued/offline replay retained structured sources/generated-image metadata; obsolete v1 bridge classes retired.
- v1.03: Messages and read-only Observe gained dedicated native screen owners.
- v1.04: client-side Copy/Share duplication, full-tree typing lag and stray Observe-guide regression fixed with idempotent/debounced decorators; published APK verified.
- v1.05: Android system Back now traverses JANUS subpages/top-level pages before exit; persisted device background activity is injected at the hidden authenticated Chat transport boundary; published APK verified.

## v1.06 — natural thought queries + active persistent Fano attention
### Device-observed failure after v1.05
Natural prompts such as `what have you been thinking about?` and `any thoughts between messages yet` still received the server's generic no-background-thinking response. The bridge itself was working, but its trigger required explicit away/background wording, so these natural forms bypassed the local activity context.

### v1.06 thought-bridge remediation
- Natural direct questions about what JANUS has been thinking now activate the local activity bridge without requiring the exact phrase `while I was away`.
- Explicit `between messages`, `between chats`, `since we spoke`, `background`, `while idle`, and similar forms are recognized.
- Ordinary topical questions such as `what do you think about X?` are intentionally not treated as requests for background history.
- The bridge states that persisted local cycles are real app-side deterministic JANUS processing with zero model/API calls, while preserving the no-phenomenal-consciousness boundary.
- Current per-core Fano direction/orientation/salience is included in the hidden device context so the conversational response can accurately explain which computational lenses dominated recent processing.

### v1.06 Fano-policy deepening
The previous runtime persisted eight Fano weights and selected one of seven directions each cycle, but the direction mainly appeared as metadata in the core summary. v1.06 makes it an active attention policy.

Seven directions now map to seven computational orientations:
1. grounding/support;
2. structure/causality;
3. counterexample/falsification;
4. context/relationships;
5. continuity/memory;
6. boundary/risk;
7. novelty/adjacent possibility.

For every specialist, hemisphere, Consensus and Interface cycle:
- the persistent Fano state selects an active direction;
- the direction supplies an explicit attention directive that changes what that core prioritizes in its externalizable processing result;
- accumulated weights produce a directional salience percentage;
- the existing 1|3|4 projection remains visible as origin / line / off-line state;
- the orientation, salience, directive and projection propagate forward with the core output through the existing 7 -> 2 -> 1 -> 1 topology;
- Observe/status exposes `active_orientation` and `active_salience_percent` for each core;
- Chat receives these orientations only as bounded hidden device context when background activity is relevant.

Important interpretation boundary: this makes the Fano state computationally consequential inside JANUS, but does not treat the Fano plane or JANUS mathematics as evidence that any external factual claim is true.

## v1.06 release rule
Do not merge until:
1. v1.06 natural-query and active-Fano regression gate passes;
2. v1.04 Chat performance regression gate remains green;
3. navigation, structured Chat, maintenance/auth/protocol checks remain green;
4. authoritative Java compilation succeeds;
5. APK assembly succeeds;
6. after merge, `apk-download` records `Publish JANUS Android native v1.06`.

## After v1.06
Real-device validation should ask both `what have you been thinking about?` and `any thoughts between messages yet`, confirm that JANUS summarizes actual persisted local activity instead of denying it, inspect Observe for changing Fano orientations/salience, and confirm Android Back plus v1.04 typing responsiveness remain stable. After that, resume reducing `MainActivity` responsibilities and improve wider-screen/tablet layouts.
