from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable

from .senses import Appraisal

FACULTIES = {
    1: ("truth", "grounding / evidence / confidence"),
    2: ("valence", "value / welfare / goals / boundaries"),
    3: ("significance", "consequence / conflict / salience"),
    4: ("pattern", "relationship / context / structure"),
    5: ("understanding", "model / causality / consistency"),
    6: ("possibility", "imagination / alternatives / direction"),
    7: ("continuity", "memory / history / learned appraisal"),
}

FANO_LINES = ((1,2,3),(1,4,5),(1,6,7),(2,4,6),(2,5,7),(3,4,7),(3,5,6))

ROLE_BIASES: dict[str, dict[int, int]] = {
    "evidence": {1:5,5:2,3:1},
    "safety": {2:5,3:2,7:1},
    "counterpoint": {3:5,1:2,2:2,5:1},
    "context": {4:5,6:2,7:1},
    "logic": {5:5,1:2,4:2,3:1},
    "novelty": {6:5,4:2,2:2,5:1},
    "memory": {7:5,1:1,2:1,4:1,5:1},
    "left_hemisphere": {5:5,1:3,3:2,7:1},
    "right_hemisphere": {6:5,4:4,7:2,2:1},
    "front": {3:4,2:3,7:3,5:2,6:1},
    "interface": {3:3,2:3,5:2,6:2,1:2,7:1},
}

CUES: dict[int, tuple[str, ...]] = {
    1: ("evidence","source","fact","true","false","claim","support","verify","confidence"),
    2: ("want","prefer","good","bad","harm","benefit","safe","unsafe","privacy","boundary","goal"),
    3: ("important","urgent","risk","conflict","contradict","however","but","failure","consequence"),
    4: ("pattern","context","relationship","similar","structure","system","environment","analogy"),
    5: ("because","cause","logic","model","therefore","constraint","explain","predict","consistent"),
    6: ("could","might","possible","idea","alternative","imagine","create","explore","option","future"),
    7: ("remember","before","again","history","previous","continuity","memory","learned","past"),
}


def _clip(value: str, n: int = 700) -> str:
    return " ".join((value or "").split())[:n]


def _words(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9][a-z0-9_-]{2,}", (value or "").lower()))


@dataclass
class RecursiveCoreState:
    core_name: str
    weights: list[int] = field(default_factory=lambda: [8,1,1,1,1,1,1,1])
    active_direction: int = 0
    revision_count: int = 0
    peer_turn_count: int = 0
    ai_capable: bool = True
    ai_last: str = ""
    last_conclusion: str = ""
    last_faculties: dict[int, str] = field(default_factory=dict)

    def snapshot(self) -> dict[str, Any]:
        line = self.weights[1] + self.weights[2] + self.weights[3]
        off = self.weights[4] + self.weights[5] + self.weights[6] + self.weights[7]
        return {
            "core": self.core_name,
            "recursive_janus": True,
            "ai_capable": self.ai_capable,
            "active_direction": self.active_direction,
            "active_faculty": FACULTIES.get(self.active_direction, ("reference", "uncommitted"))[0],
            "weights": list(self.weights),
            "projection_1_3_4": {"origin": self.weights[0], "line": line, "off_line": off},
            "revision_count": self.revision_count,
            "peer_turn_count": self.peer_turn_count,
            "faculties": {str(k): v for k, v in self.last_faculties.items()},
            "conclusion": self.last_conclusion,
            "ai_last": self.ai_last,
        }


class RecursiveCoreProcessor:
    """One complete JANUS/Fano processor used inside every top-level core.

    The outer core role is a disposition/bias, not the removal of faculties. Every
    core evaluates all seven non-zero Fano positions, forms a conclusion, receives
    peer conclusions, and can revise. AI inference can later contribute bounded
    counsel without replacing the deterministic recursive state.
    """

    def think(
        self,
        state: RecursiveCoreState,
        content: str,
        appraisal: Appraisal,
        role_purpose: str,
        peers: Iterable[tuple[str, str]] = (),
        ai_counsel: str = "",
    ) -> dict[str, Any]:
        text = _clip(content, 5000)
        low = text.lower()
        words = _words(low)
        peer_list = [(str(n), _clip(str(s), 500)) for n, s in peers if str(s).strip() and str(n) != state.core_name]
        peer_text = " ".join(s for _, s in peer_list).lower()
        peer_words = _words(peer_text)
        scores: dict[int, int] = {}
        bias = ROLE_BIASES.get(state.core_name, {})
        for d in range(1, 8):
            cue_hits = sum(1 for cue in CUES[d] if cue in low)
            peer_hits = sum(1 for cue in CUES[d] if cue in peer_text)
            score = 2 + cue_hits * 2 + min(4, peer_hits) + bias.get(d, 0)
            if d == 1: score += int(round(appraisal.confidence * 3))
            elif d == 2: score += int(round((abs(appraisal.valence) + appraisal.risk) * 2))
            elif d == 3: score += int(round((appraisal.salience + appraisal.conflict + appraisal.urgency) * 2))
            elif d == 4: score += min(3, len(words & peer_words))
            elif d == 5: score += int(round((appraisal.confidence + (1.0-appraisal.uncertainty)) * 2))
            elif d == 6: score += int(round((appraisal.novelty + appraisal.opportunity) * 2))
            elif d == 7: score += int(round(appraisal.familiarity * 4))
            scores[d] = score
            state.weights[d] += max(1, score)
        state.weights[0] += 1
        state.active_direction = max(scores, key=scores.get)
        if peer_list:
            state.peer_turn_count += len(peer_list)
            state.revision_count += 1
        if ai_counsel.strip():
            state.ai_last = _clip(ai_counsel, 900)
            state.revision_count += 1

        faculties: dict[int, str] = {}
        for d, (label, meaning) in FACULTIES.items():
            peer_note = ""
            if peer_list and any(c in peer_text for c in CUES[d]):
                peer_note = " Peer material adds pressure here."
            faculties[d] = f"{label}: {meaning}; activation={scores[d]}.{peer_note}"
        state.last_faculties = faculties

        active_label = FACULTIES[state.active_direction][0]
        peer_clause = f"; revised against {len(peer_list)} peer core states" if peer_list else ""
        ai_clause = "; incorporated bounded AI counsel" if ai_counsel.strip() else ""
        state.last_conclusion = _clip(
            f"{state.core_name} ran a complete internal JANUS/Fano readout across all seven faculties. "
            f"Outer disposition: {role_purpose}. Dominant internal faculty this pass: d{state.active_direction} {active_label}"
            f"{peer_clause}{ai_clause}. Focus: {text}",
            1600,
        )
        for i, v in enumerate(state.weights):
            if v > 5000:
                state.weights[i] = max(1, v // 2)
        return state.snapshot()


def apply_ai_counsel(state: RecursiveCoreState, counsel: str) -> None:
    clean = _clip(counsel, 900)
    if not clean:
        return
    state.ai_last = clean
    state.revision_count += 1
