# JANUS checkpoint — Step 4 unified cost/accounting governor

Date: 2026-08-22

Step 4 of the post-Step-7 roadmap is implemented server-side.

## What changed

- Added `cost_governor.py`, a profile-scoped SQLite ledger for external-compute events and denied calls.
- Unified capability classes: chat, foreground_core, background_model, background_web, vision, image, maintenance and other.
- Added configurable per-profile daily/monthly estimated-cost ceilings, a separate tighter background daily ceiling, and a global daily ceiling.
- Added environment-configurable reservation estimates for every capability. These are budgeting estimates only, explicitly not provider invoices.
- Provider token usage is recorded when a response exposes usage metadata.
- Added `cost_governor_hooks.py` to wrap the OpenAI client aliases used by foreground core deliberation, background consultation/web curiosity, persistent vision, image generation and final Interface chat.
- Background model/web work is classified as optional and can be throttled before foreground chat reaches the broader profile ceiling.
- Existing caching remains upstream of provider calls, so cache hits do not incur new cost events.
- `image_response_compat.py` activates the hooks in the live bootstrap path, scopes chat by profile and exposes `/desktop/cost-status?username=...`.
- Chat responses carry a current cost-governor status block for diagnostics/UI use.

## Default planning limits

Defaults are deliberately conservative but configurable without code changes:
- profile daily estimated budget: USD 2.00
- profile monthly estimated budget: USD 30.00
- optional background daily estimated budget: USD 0.50
- global daily estimated budget: USD 100.00

Capability reservation defaults are small planning values and can be overridden independently with `JANUS_COST_RESERVE_<CAPABILITY>_USD`.

## Safety/continuity boundary

The governor does not change protected JANUS identity, memory or reasoning state. A denied optional call degrades to deterministic/local processing where the existing subsystem already supports that. It does not erase pending work. Budgeting is account/profile isolated.

## Tests

`tests/test_cost_governor.py` covers:
- per-profile accounting and isolation;
- hard daily denial;
- optional-background throttling before foreground chat;
- nested context restoration.

The main cognition CI now watches, compiles and tests the cost-governor stack.

## Next roadmap item

Step 5: maintenance/upgrade request system — turn the existing maintenance-review foundation into an approximately quarterly technology/security/dependency/model review that creates a user-facing proposal and never silently self-modifies protected architecture.
