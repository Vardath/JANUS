from __future__ import annotations

from typing import Any

from .topology import CORE_NAMES


def tick(mind: Any, account_id: int) -> dict[str, int]:
    """Run one deterministic all-11 recursive peer cycle with zero external calls."""
    if not hasattr(mind, "_recursive_states") or not hasattr(mind, "_processor"):
        return {"cores": 0, "peer_revisions": 0, "model_calls": 0}
    aid = int(account_id)
    outer = mind._states(aid)
    nested = mind._recursive_states(aid)
    first: dict[str, str] = {}
    for name in CORE_NAMES:
        outer_state = outer[name]
        stimulus = outer_state.last_public_summary or f"retained background state for {name}"
        result = mind._processor.think(
            nested[name], stimulus, outer_state.appraisal, mind._purpose(name), []
        )
        first[name] = result.get("conclusion", "")

    revisions = 0
    for name in CORE_NAMES:
        peers = [(peer, summary) for peer, summary in first.items() if peer != name and summary]
        mind._processor.think(
            nested[name], nested[name].last_conclusion or "background peer revision",
            outer[name].appraisal, mind._purpose(name), peers
        )
        revisions += len(peers)
    return {"cores": len(CORE_NAMES), "peer_revisions": revisions, "model_calls": 0}
