# JANUS Step 8 — Visual Explanation Intelligence

Date: 2026-08-22
Status: IMPLEMENTED; CI/live validation pending.

Step 8 adds a zero-cost decision layer between an Interface visual nomination and the existing Stage-1 image renderer. The Interface may still nominate at most one optional visual inside the normal Chat turn, but an unsolicited image is now rendered only when a local deterministic policy finds material explanatory value.

`visual_explanation.py` scores automatic nominations for genuinely visual/spatial subject matter (geometry, topology, architecture, flow, circuits, lattice/projection/layout, hierarchy, comparison, etc.), explanatory user intent, substantive answer depth and a sufficiently specific visual brief. Routine operational topics such as server diagnostics, telemetry, heartbeat, workflow/build status, login/billing and maintenance status are explicitly rejected. Short/decorative nominations are also rejected.

Explicit user image requests bypass this explanatory-value gate and continue through the existing Stage-1 renderer, medium-quality default, account/global image caps, cooldown/caching and unified cost governor. The Step-8 gate therefore cannot prevent an explicit user request merely because the subject is simple.

When an automatic nomination is declined, the hidden `[[JANUS_VISUAL: ...]]` marker is removed from the user-facing answer and the renderer is never called. Accepted automatic nominations continue through existing `generate_for_account(... origin='auto')`, preserving all hard budget/cooldown/caching controls. The response includes inspectable `visual_decision` metadata for diagnostics.

`image_response_compat.py` installs the policy after the image-generation module is loaded. No background render loop is enabled. Multi-core visual deliberation remains disabled and revenue-gated as planned.

Regression tests cover acceptance of a material spatial explanation, rejection of diagnostics and decorative nominations, preservation of explicit user requests, and proof that a declined automatic nomination never calls the renderer. The cognition CI now compiles and runs the Step-8 policy tests.

Next roadmap item: Step 9 — revenue-gated multi-core visual deliberation scaffolding only; actual autonomous background rendering remains disabled.
