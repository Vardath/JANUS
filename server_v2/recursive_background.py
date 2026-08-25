from __future__ import annotations

from typing import Any

from . import storage
from .topology import CORE_NAMES, FRONT_CORE


def tick(mind: Any, account_id: int) -> dict[str, int]:
    """Run one bounded all-11 peer cycle only while awake, with memory recall."""
    if getattr(mind, "phase", "wake") != "wake":
        return {"cores": 0, "peer_revisions": 0, "changed_cores": 0, "quiescent": 1, "model_calls": 0}
    if not hasattr(mind, "_recursive_states") or not hasattr(mind, "_processor"):
        return {"cores": 0, "peer_revisions": 0, "changed_cores": 0, "quiescent": 1, "model_calls": 0}
    aid = int(account_id)
    outer = mind._states(aid); nested = mind._recursive_states(aid)
    remembered = storage.list_memories(aid, 6)
    memory_digest = " | ".join(str(m.get("content") or "")[:260] for m in remembered[:6])
    first: dict[str, str] = {}; changed = 0
    for name in CORE_NAMES:
        outer_state = outer[name]
        stimulus = outer_state.last_public_summary or f"retained background state for {name}"
        if memory_digest:
            stimulus += " | recalled interaction memory: " + memory_digest
        result = mind._processor.think(nested[name], stimulus, outer_state.appraisal, mind._purpose(name), [])
        first[name] = result.get("conclusion", "")
        if result.get("changed"): changed += 1
    if changed == 0:
        return {"cores": len(CORE_NAMES), "peer_revisions": 0, "changed_cores": 0, "quiescent": 1, "model_calls": 0}

    revisions = 0
    for name in CORE_NAMES:
        peers = [(peer, summary) for peer, summary in first.items() if peer != name and summary]
        result = mind._processor.think(nested[name], nested[name].last_conclusion or "background peer revision",
                                       outer[name].appraisal, mind._purpose(name), peers)
        if result.get("changed"):
            revisions += len(peers)
    storage.add_event(
        aid, FRONT_CORE, "recursive_peer_exchange",
        f"Wake cycle: {changed} recursive cores materially changed; {revisions} bounded peer-revision links processed; recent user interaction memory was {'recalled' if memory_digest else 'not available'}; model calls=0.",
        mode="background",
    )
    return {"cores": len(CORE_NAMES), "peer_revisions": revisions, "changed_cores": changed, "quiescent": 0, "model_calls": 0}
