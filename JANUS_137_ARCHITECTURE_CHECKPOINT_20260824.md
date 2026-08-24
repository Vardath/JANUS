# JANUS 1-3-7 architecture checkpoint — 2026-08-24

## Status
DESIGN CHECKPOINT ONLY. Preserve current working code. Do not implement this architecture merely from this record; owner intends to continue from here next session and explicitly authorize implementation.

## Correct conceptual architecture
JANUS is a **1 | 3 | 7** functional architecture.

### 1 — Interface core
- The single outward conversational speaker.
- Receives user interaction and returns the final user-facing response.
- It is NOT one of the three background intermediaries.
- It should not pretend to expose private chain-of-thought or phenomenal consciousness.

### 3 — Background/intermediary mind
The three are:
1. central background/bridge core;
2. left-hemisphere core;
3. right-hemisphere core.

The central background/bridge core communicates directly with the Interface and coordinates/integrates the two hemispheres. The two hemispheres receive and sort subconscious material with complementary functional biases, preserve useful disagreement, and pass integrated material upward.

### 7 — Subconscious cores
- Seven distinct background worker/evaluator minds.
- Every relevant user interaction is visible to all seven so each can form its own operational assessment/projection and begin appropriate work.
- They should be able to pass useful work among themselves and upward rather than behaving as seven cosmetic labels.
- Their work is synthesized by the hemisphere layer rather than dumped directly into chat.

## Flow and notation
Operational dataflow may be written:

`7 subconscious -> 2 hemispheres -> 1 central background/bridge -> 1 Interface`

But the conceptual JANUS hierarchy is **1-3-7**, because the central background/bridge plus the two hemispheres are the middle three, while the Interface is the separate outward one.

The current UI shorthand `7 -> 2 -> 1 -> 1` is mechanically descriptive but must not obscure the conceptual 1-3-7 architecture.

## Fano/JANUS structural idea to implement carefully next
The seven subconscious cores should be operationally related to the seven nonzero points of F2^3/Fano structure, with the zero/reference state completing the eight-state structure. Do NOT collapse this into merely three semantic binary evaluator cores: the user explicitly corrected that interpretation. There are seven operational subconscious values/positions; the three binary coordinates are mathematical coordinates, not the count of functional subconscious minds.

Next design work should determine, rigorously and explicitly:
- what each of the seven Fano-projection states means operationally to an AI core;
- how the zero/reference state functions;
- how Fano lines/relations control exchange, combination, disagreement, routing or transitions among subconscious cores;
- how state/projection affects attention, evaluation and candidate output without numerology or arbitrary hard-coding;
- how hemispheric specialization receives these seven streams;
- how the bridge/background core maintains persistent integrated working state;
- how the Interface uses that state while remaining one coherent speaker;
- how to test that the structure has real behavioral effect rather than being telemetry decoration.

## User interaction semantics
A user request is broadcast into the internal functional system so relevant background work can begin. The final response should reflect the integrated system, not expose raw internal traces.

Important intent distinction: when the user asks JANUS to **think/ponder/work on** a subject, JANUS should recognize that as a request to begin/continue bounded background work. It should normally acknowledge the request concisely instead of immediately substituting its current assessment as though the requested pondering had already happened. Later reports should be grounded in actual persisted background activity/events, with no claims of phenomenal/private consciousness.

## Existing product/runtime concerns retained
Recent Android work established/fixed chat spam/performance, background deterministic processing reporting, Android Back/navigation/chrome/Cores behavior, maintenance request isolation, and governance. Do not regress those while implementing 1-3-7. Existing maintenance isolation remains important: JANUS stores capability/maintenance requests in its own persistent server storage and is not given GitHub credentials/source-write primitives. Repo review and implementation remain Supervisor/owner-mediated.

## Next-session instruction
When the owner asks to review/recall the private repo and continue JANUS work:
1. reconstruct current repo/main and recent interaction history thoroughly;
2. read this checkpoint and the maintenance isolation/current progress records;
3. check pending JANUS maintenance requests and Supervisor decision/import/deployment state;
4. verify current CI/runtime state rather than assuming prior merges deployed;
5. double-check and triple-check architecture-impacting changes and regression risks;
6. preserve the exact mathematical JANUS results separately from experimental functional/agency interpretations;
7. propose/confirm the operational semantics for the seven Fano subconscious states before making the structural implementation, unless the owner explicitly tells you to proceed directly;
8. after authorized work, update private repo records with latest interactions, decisions, actions, verification, remaining work and exact stopping state.

## Stopping point
The corrected architecture is now: **1 Interface; 3 background intermediaries = central background/bridge + left hemisphere + right hemisphere; 7 subconscious cores.** Next session is intended to design/implement the operational 1-3-7/Fano structure from this checkpoint.