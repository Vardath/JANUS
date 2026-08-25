from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SpecialistRole:
    name: str
    direction: int
    axes: tuple[str, ...]
    meaning: str
    purpose: str


# These seven names are OUTER dispositions of seven complete JANUS cores. They are
# not the seven faculties inside those cores. Every top-level core (including both
# hemispheres, Front and Interface) internally retains all seven Fano faculties:
# d1 truth, d2 valence, d3 significance, d4 pattern, d5 understanding,
# d6 possibility, d7 continuity.
SPECIALIST_ROLES = {
    "evidence": SpecialistRole(
        "evidence", 1, ("E",), "truth / grounding",
        "bias a complete internal JANUS readout toward what is present, supported and confidently grounded",
    ),
    "safety": SpecialistRole(
        "safety", 2, ("V",), "valence / welfare / boundary",
        "bias a complete internal JANUS readout toward good/bad, wanted/unwanted, welfare, goals, boundaries and reversibility",
    ),
    "counterpoint": SpecialistRole(
        "counterpoint", 3, ("E", "V"), "significance / conflict / consequence",
        "bias a complete internal JANUS readout toward consequential contradiction, objection, risk and why disagreement matters",
    ),
    "context": SpecialistRole(
        "context", 4, ("P",), "pattern / relationship / environment",
        "bias a complete internal JANUS readout toward relationships, framing, analogy, situational context and larger configuration",
    ),
    "logic": SpecialistRole(
        "logic", 5, ("E", "P"), "understanding / model / causality",
        "bias a complete internal JANUS readout toward coherent models, constraints, explanations, predictions and falsifiability",
    ),
    "novelty": SpecialistRole(
        "novelty", 6, ("V", "P"), "possibility / imagination / direction",
        "bias a complete internal JANUS readout toward useful alternatives, opportunities, future paths and testable creative hypotheses",
    ),
    "memory": SpecialistRole(
        "memory", 7, ("E", "V", "P"), "continuity / learned appraisal / experience",
        "bias a complete internal JANUS readout toward retained history, learned significance, prior outcomes and unfinished threads",
    ),
}

SPECIALIST_DIRECTIONS = {name: role.direction for name, role in SPECIALIST_ROLES.items()}
DIRECTION_SPECIALISTS = {role.direction: name for name, role in SPECIALIST_ROLES.items()}

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
        "purpose": "run its own complete JANUS processor while constraining the whole society into explicit, sequential, causal and consistency-focused interpretations",
    },
    "right_hemisphere": {
        "meaning": "imagination / association / expansion",
        "purpose": "run its own complete JANUS processor while expanding the whole society through contextual, gestalt, relational, alternative and generative interpretations",
    },
}

FRONT_CORE = "front"
INTERFACE_CORE = "interface"
CORE_NAMES = (*SPECIALIST_ROLES.keys(), *HEMISPHERE_ROLES.keys(), FRONT_CORE, INTERFACE_CORE)
ARCHITECTURE = "recursive 1-3-7: 11 top-level cores, each containing a complete seven-position JANUS/Fano processor"
MECHANICAL_FLOW = "7 -> 2 -> 1 -> 1"


def _recursive_fields() -> dict:
    return {
        "recursive_janus": True,
        "internal_fano_faculties": {
            1: "truth", 2: "valence", 3: "significance", 4: "pattern",
            5: "understanding", 6: "possibility", 7: "continuity",
        },
        "peer_responsive": True,
        "ai_capable": True,
        "semantics": "outer role is a disposition; every core retains all internal JANUS/Fano faculties; Fano state never establishes external truth",
    }


def metadata(core_name: str) -> dict:
    common = _recursive_fields()
    if core_name in SPECIALIST_ROLES:
        role = SPECIALIST_ROLES[core_name]
        return {
            **common,
            "layer": "subconscious",
            "home_direction": role.direction,
            "axes": list(role.axes),
            "meaning": role.meaning,
            "purpose": role.purpose,
        }
    if core_name in HEMISPHERE_ROLES:
        role = HEMISPHERE_ROLES[core_name]
        return {
            **common,
            "layer": "intermediary",
            "home_direction": 0,
            "meaning": role["meaning"],
            "purpose": role["purpose"],
        }
    if core_name == FRONT_CORE:
        return {
            **common,
            "layer": "intermediary",
            "home_direction": 0,
            "meaning": "affective appraisal / intention / bridge",
            "purpose": "run a complete JANUS readout over hemisphere and peer states, preserve disagreement, and form bounded integrated appraisal/intention",
        }
    if core_name == INTERFACE_CORE:
        return {
            **common,
            "layer": "interface",
            "home_direction": 0,
            "meaning": "expression / interaction / action",
            "purpose": "run a complete JANUS readout over the integrated society, determine how it should meet the user/environment, and select expression or bounded action",
        }
    raise KeyError(core_name)


def validate_fano_contract() -> None:
    assert set(SPECIALIST_DIRECTIONS.values()) == set(range(1, 8))
    for a, b, c in FANO_LINES:
        assert a ^ b == c or a ^ c == b or b ^ c == a
