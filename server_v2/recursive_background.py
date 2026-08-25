from __future__ import annotations

import hashlib
from typing import Any

from . import storage
from .topology import CORE_NAMES, FRONT_CORE


def _fingerprint(parts: list[str]) -> str:
    return hashlib.sha256("\n".join(parts).encode("utf-8", errors="ignore")).hexdigest()[:24]


def tick(mind: Any, account_id: int) -> dict[str, int]:
    """Run one bounded all-11 peer cycle only when retained inputs materially changed."""
    if getattr(mind, "phase", "wake") != "wake":
        return {"cores": 0, "peer_revisions": 0, "model_calls": 0}
    if not hasattr(mind, "_recursive_states") or not hasattr(mind, "_processor"):
        return {"cores": 0, "peer_revisions": 0, "model_calls": 0}
    aid = int(account_id)
    outer = mind._states(aid); nested = mind._recursive_states(aid)
    try:
        remembered = storage.list_memories(aid, 6)
    except Exception:
        remembered = []
    memory_digest = " | ".join(str(m.get("content") or "")[:260] for m in remembered[:6])
    retained = [f"{name}:{outer[name].last_public_summary}" for name in CORE_NAMES]
    fp = _fingerprint(retained + [memory_digest])
    fingerprints = getattr(mind, "_background_fingerprints", None)
    if fingerprints is None:
        fingerprints = {}; setattr(mind, "_background_fingerprints", fingerprints)
    if fingerprints.get(aid) == fp:
        return {"cores": len(CORE_NAMES), "peer_revisions": 0, "model_calls": 0}
    fingerprints[aid] = fp

    first: dict[str, str] = {}
    for name in CORE_NAMES:
        outer_state = outer[name]
        stimulus = outer_state.last_public_summary or f"retained background state for {name}"
        if memory_digest: stimulus += " | recalled interaction memory: " + memory_digest
        result = mind._processor.think(nested[name], stimulus, outer_state.appraisal, mind._purpose(name), [], force=True)
        first[name] = result.get("conclusion", "")

    revisions = 0
    for name in CORE_NAMES:
        peers = [(peer, summary) for peer, summary in first.items() if peer != name and summary]
        result = mind._processor.think(nested[name], "background peer revision", outer[name].appraisal, mind._purpose(name), peers, force=True)
        if result.get("changed"): revisions += len(peers)
    try:
        storage.add_event(aid, FRONT_CORE, "recursive_peer_exchange",
            f"Wake cycle: {len(CORE_NAMES)} recursive cores processed changed retained input; {revisions} bounded peer-revision links processed; recent user interaction memory was {'recalled' if memory_digest else 'not available'}; model calls=0.",
            mode="background")
    except Exception:
        pass
    return {"cores": len(CORE_NAMES), "peer_revisions": revisions, "model_calls": 0}
