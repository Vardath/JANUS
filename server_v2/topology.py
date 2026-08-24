from __future__ import annotations

SPECIALIST_DIRECTIONS = {
    "evidence": 1,
    "logic": 2,
    "counterpoint": 3,
    "context": 4,
    "memory": 5,
    "safety": 6,
    "novelty": 7,
}

# Canonical Fano-plane line triples over the seven non-zero directions of F2^3.
FANO_LINES = (
    (1,2,3), (1,4,5), (1,6,7),
    (2,4,6), (2,5,7), (3,4,7), (3,5,6),
)


def metadata(core_name: str) -> dict:
    if core_name in SPECIALIST_DIRECTIONS:
        return {
            "active_direction": SPECIALIST_DIRECTIONS[core_name],
            "semantics": "processing-bias/index only; never a truth oracle",
        }
    return {
        "active_direction": 0,
        "semantics": "integrator core; Fano directions arrive through specialists",
    }
