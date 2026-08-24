from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SpecialistRole:
    name: str
    direction: int
    axes: tuple[str, ...]
    meaning: str
    purpose: str


# The original seven JANUS specialist names are preserved. Their Fano numbers now
# arise from three primitive cognitive coordinates instead of arbitrary numbering:
# E = epistemic/truth, V = valence/welfare, P = pattern/relationship.
SPECIALIST_ROLES = {
    "evidence": SpecialistRole(
        "evidence", 1, ("E",), "truth / grounding",
        "sense what is present, separate support from inference, and calibrate confidence",
    ),
    "safety": SpecialistRole(
        "safety", 2, ("V",), "valence / welfare / boundary",
        "sense good/bad, wanted/unwanted, benefit/harm, user goals, boundaries, and reversibility",
    ),
    "counterpoint": SpecialistRole(
        "counterpoint", 3, ("E", "V"), "significance / conflict / consequence",
        "detect consequential contradiction, objection, risk, salience, and reasons the current view may matter or fail",
    ),
    "context": SpecialistRole(
        "context", 4, ("P",), "pattern / relationship / environment",
        "sense relationships, framing, analogy, situational context, and larger configuration",
    ),
    "logic": SpecialistRole(
        "logic", 5, ("E", "P"), "understanding / model / causality",
        "turn grounded patterns into coherent models, constraints, explanations, predictions, and falsifiable structure",
    ),
    "novelty": SpecialistRole(
        "novelty", 6, ("V", "P"), "possibility / imagination / direction",
        "generate useful alternatives, opportunities, future paths, creative hypotheses, and testable adjacent possibilities",
    ),
    "memory": SpecialistRole(
        "memory", 7, ("E", "V", "P"), "continuity / learned appraisal / experience",
        "compare present sensing with retained history, learned significance, unfinished threads, and identity continuity",
    ),
}

SPECIALIST_DIRECTIONS = {name: role.direction for name, role in SPECIALIST_ROLES.items()}
DIRECTION_SPECIALISTS = {role.direction: name for name, role in SPECIALIST_ROLES.items()}

# Canonical Fano-plane line triples over F2^3. Each triple has XOR closure: a ^ b = c.
# With the semantics above these lines have operational meanings such as
# Evidence + Safety -> Counterpoint/significance and Evidence + Context -> Logic/model.
FANO_LINES = (
    (1, 2, 3),
    (1, 4, 5),
    (1, 6, 7),
    (2, 4, 6),
    (2, 5, 7),
    (3, 4, 7),
    (3, 5, 6),
)

HEMISPHERE_ROLES = {
    "left_hemisphere": {
        "meaning": "logic / discrimination / constraint",
        "purpose": "receive all seven subconscious projections and build explicit, sequential, causal, consistency-focused interpretations",
    },
    "right_hemisphere": {
        "meaning": "imagination / association / expansion",
        "purpose": "receive all seven subconscious projections and build contextual, gestalt, relational, alternative and generative interpretations",
    },
}

FRONT_CORE = "front"
INTERFACE_CORE = "interface"
CORE_NAMES = (*SPECIALIST_ROLES.keys(), *HEMISPHERE_ROLES.keys(), FRONT_CORE, INTERFACE_CORE)
ARCHITECTURE = "1-3-7: 7 subconscious projections -> left/right hemispheres -> front/bridge -> interface"
MECHANICAL_FLOW = "7 -> 2 -> 1 -> 1"


def metadata(core_name: str) -> dict:
    if core_name in SPECIALIST_ROLES:
        role = SPECIALIST_ROLES[core_name]
        return {
            "layer": "subconscious",
            "home_direction": role.direction,
            "axes": list(role.axes),
            "meaning": role.meaning,
            "purpose": role.purpose,
            "semantics": "Fano projection is a processing lens; never a truth oracle",
        }
    if core_name in HEMISPHERE_ROLES:
        role = HEMISPHERE_ROLES[core_name]
        return {
            "layer": "intermediary",
            "home_direction": 0,
            "meaning": role["meaning"],
            "purpose": role["purpose"],
            "semantics": "receives all seven projections; preserves useful disagreement",
        }
    if core_name == FRONT_CORE:
        return {
            "layer": "intermediary",
            "home_direction": 0,
            "meaning": "affective appraisal / intention / bridge",
            "purpose": "feel out confidence, valence, salience, uncertainty, urgency, conflict, risk, opportunity and readiness to act before presentation",
            "semantics": "integrates hemispheres without claiming biological feeling or phenomenal consciousness",
        }
    if core_name == INTERFACE_CORE:
        return {
            "layer": "interface",
            "home_direction": 0,
            "meaning": "expression / interaction / action",
            "purpose": "feel out how the integrated state should meet the user/environment, choose an appropriate response or bounded action, and observe consequences as new sensory input",
            "semantics": "outward speaker/action selector; results re-enter as new sensing, not recursive self-chat",
        }
    raise KeyError(core_name)


def validate_fano_contract() -> None:
    assert set(SPECIALIST_DIRECTIONS.values()) == set(range(1, 8))
    for a, b, c in FANO_LINES:
        assert a ^ b == c or a ^ c == b or b ^ c == a
