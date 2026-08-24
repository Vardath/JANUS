from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


SENSORY_MODALITIES = (
    "text",
    "image",
    "audio",
    "file",
    "web",
    "memory",
    "runtime",
    "peer",
    "action_result",
)

AFFECT_DIMENSIONS = (
    "confidence",
    "valence",
    "salience",
    "uncertainty",
    "novelty",
    "urgency",
    "familiarity",
    "risk",
    "opportunity",
    "conflict",
)


def _unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _signed(value: float) -> float:
    return max(-1.0, min(1.0, float(value)))


@dataclass(frozen=True)
class SenseFrame:
    """A bounded, inspectable sensory event available to every core in one society.

    This is a computational sensing contract, not a claim of biological sensation.
    Local and global societies produce and exchange SenseFrames without overwriting
    one another's private persistent state.
    """

    modality: str
    source: str
    content: str
    salience: float = 0.5
    uncertainty: float = 0.5
    novelty: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.modality not in SENSORY_MODALITIES:
            raise ValueError(f"unsupported sensory modality: {self.modality}")
        object.__setattr__(self, "salience", _unit(self.salience))
        object.__setattr__(self, "uncertainty", _unit(self.uncertainty))
        object.__setattr__(self, "novelty", _unit(self.novelty))


@dataclass(frozen=True)
class Appraisal:
    """Externalizable affect-like control state used by Front and Interface.

    The dimensions regulate attention, response style and bounded action selection.
    They must not be described as proof of phenomenal feeling.
    """

    confidence: float = 0.5
    valence: float = 0.0
    salience: float = 0.5
    uncertainty: float = 0.5
    novelty: float = 0.5
    urgency: float = 0.0
    familiarity: float = 0.5
    risk: float = 0.0
    opportunity: float = 0.0
    conflict: float = 0.0

    def __post_init__(self) -> None:
        for name in ("confidence", "salience", "uncertainty", "novelty", "urgency", "familiarity", "risk", "opportunity", "conflict"):
            object.__setattr__(self, name, _unit(getattr(self, name)))
        object.__setattr__(self, "valence", _signed(self.valence))

    def as_dict(self) -> dict[str, float]:
        return {name: float(getattr(self, name)) for name in AFFECT_DIMENSIONS}

    def action_posture(self) -> str:
        if self.risk >= 0.8 and self.urgency >= 0.6:
            return "interrupt_or_warn"
        if self.conflict >= 0.7 or self.uncertainty >= 0.75:
            return "clarify_or_preserve_uncertainty"
        if self.opportunity >= 0.7 and self.risk <= 0.4:
            return "explore_or_act"
        if self.salience <= 0.25:
            return "defer_or_observe"
        return "respond_normally"


def merge_appraisals(*items: Appraisal) -> Appraisal:
    if not items:
        return Appraisal()
    n = float(len(items))
    return Appraisal(
        confidence=sum(x.confidence for x in items) / n,
        valence=sum(x.valence for x in items) / n,
        salience=max(x.salience for x in items),
        uncertainty=max(x.uncertainty for x in items),
        novelty=max(x.novelty for x in items),
        urgency=max(x.urgency for x in items),
        familiarity=sum(x.familiarity for x in items) / n,
        risk=max(x.risk for x in items),
        opportunity=max(x.opportunity for x in items),
        conflict=max(x.conflict for x in items),
    )
