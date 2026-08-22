# JANUS checkpoint — 2026-08-22 — post-Step-7 roadmap Step 6

Step 6 (richer proactive thread continuity) is implemented server-side.

- `proactive_threads.py` assigns durable thread identity to surfaced autonomous Messages.
- Thread resolution prefers explicit open continuity-ledger items when the subject overlap is strong enough; unrelated findings remain independent background threads.
- No thread operation mutates project/question lifecycle state automatically.
- Autonomous Messages retain the existing quality/rate-limit gate and gain thread provenance after successful storage.
- Thread metadata includes source event, optional source event id, title, type, optional continuity item id and match confidence.
- `/desktop/message-thread` and `/desktop/message-thread-status` expose account-scoped thread information.
- Chat can use explicit `reply_to_message_id`, `proactive_event_id` or `message_event_id`; older clients can still continue the most recent thread only under clear follow-up language or useful topic overlap.
- Follow-up grounding is stored as bounded process context without altering the user's text.
- Regression tests cover correct project/question linkage, avoidance of false linkage, follow-up continuity, explicit replies and profile isolation.

Next roadmap item: Step 7 — outbound working artifacts: JANUS-generated research notes/reports/exports stored as authenticated account-bound files, without requiring PC/Apple parity work.
