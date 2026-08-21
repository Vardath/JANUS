"""Deterministic zero-API-cost Fano/JANUS 8-state cognitive substrate.

The audited Fano mathematics supplies the state geometry. The semantic layer below
uses that geometry as a *processing-control* substrate: it can change attention,
integration pressure and which transformation a core applies, but it never creates
factual evidence and is not a physics or consciousness claim.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import re
from typing import Iterable, List, Sequence

# 000 is the distinguished/neutral state. The seven non-zero vectors of F2^3 are
# represented by integer labels 1..7. Every pair of distinct non-zero points has
# a unique Fano completion a xor b.
FANO_LABELS = (0, 1, 2, 3, 4, 5, 6, 7)
FANO_LINES = (
    (1, 2, 3), (1, 4, 5), (1, 6, 7),
    (2, 4, 6), (2, 5, 7), (3, 4, 7), (3, 5, 6),
)

# These meanings are computational policy, not newly discovered mathematics.
# They deliberately correspond to general reasoning operations rather than to
# factual subject matter, so Fano state can shape *how* a core reasons without
# manufacturing what is true.
ORIENTATION_NAMES = {
    0: "neutral",
    1: "grounding",
    2: "structure",
    3: "synthesis",
    4: "alternative",
    5: "continuity",
    6: "novelty",
    7: "boundary",
}
ORIENTATION_DIRECTIVES = {
    0: "stay conservative; preserve the current question without adding unsupported interpretation",
    1: "prioritize concrete support, observations, sources, measurements and explicit assumptions",
    2: "prioritize causal structure, constraints, consistency and relations among parts",
    3: "look for a coherent synthesis that explains how supported pieces fit together",
    4: "generate a serious alternative, counterfactual or failure mode before accepting the current view",
    5: "use temporal, historical and memory continuity; compare the present state with what persisted before",
    6: "seek a non-obvious but testable analogy, connection or new line of inquiry",
    7: "stress uncertainty, scope, safety and epistemic boundaries; separate known, inferred and speculative claims",
}

_WORD_SETS = {
    1: ("evidence", "source", "observed", "recorded", "measured", "fact", "data", "support", "verified"),
    2: ("because", "therefore", "causal", "structure", "constraint", "consistent", "logic", "relation", "mechanism"),
    3: ("combine", "together", "synthesis", "integrate", "shared", "pattern", "fit", "connect"),
    4: ("alternative", "counter", "however", "but", "fails", "wrong", "coincidence", "instead", "other"),
    5: ("memory", "history", "before", "previous", "retained", "continuity", "earlier", "persist"),
    6: ("novel", "new", "unusual", "analogy", "curious", "explore", "unexpected", "hypothesis"),
    7: ("uncertain", "unknown", "boundary", "safety", "privacy", "risk", "speculative", "tentative", "claim"),
}
_DIR_RE = re.compile(r"\bFano\s+d([0-7])\b", re.I)


def xor3(a: int, b: int) -> int:
    return (a ^ b) & 0x7


def fano_completion(a: int, b: int) -> int:
    """Return the unique third Fano point for two distinct non-zero points.

    Returns 0 for neutral/same/invalid pairings so callers can distinguish a
    genuine line-completion signal from absence of one.
    """
    a, b = int(a) & 7, int(b) & 7
    if not a or not b or a == b:
        return 0
    return xor3(a, b)


def direction_from_text(text: str) -> int:
    m = _DIR_RE.search(str(text or ""))
    return int(m.group(1)) if m else 0


@dataclass
class FanoJanusUnit:
    """Small persistent 8-state JANUS/Fano processing-control unit."""

    weights: List[int] = field(default_factory=lambda: [8, 1, 1, 1, 1, 1, 1, 1])
    step_count: int = 0
    active_direction: int = 0

    def ingest(self, texts: Iterable[str], role_salt: str = "") -> None:
        seen = False
        for text in texts:
            t = str(text or "").strip()
            if not t:
                continue
            seen = True
            digest = sha256((role_salt + "|" + t).encode("utf-8", errors="ignore")).digest()
            a = 1 + (digest[0] % 7)
            b = 1 + (digest[1] % 7)
            c = xor3(a, b)
            if c == 0:
                c = 1 + (digest[2] % 7)
            self.weights[a] += 3
            self.weights[b] += 2
            self.weights[c] += 1
            self.weights[0] += 1
        if not seen:
            self.weights[0] += 1
        self._relax()
        self.step_count += 1
        self.active_direction = max(range(8), key=lambda i: self.weights[i])

    def bias(self, direction: int, amount: int = 2) -> None:
        """Apply a small integration bias without overriding accumulated history."""
        d = max(0, min(7, int(direction)))
        if d and amount > 0:
            self.weights[d] += int(amount)
            self.active_direction = max(range(8), key=lambda i: self.weights[i])

    def _relax(self) -> None:
        total = sum(self.weights)
        mean = max(1, total // 8)
        for i, w in enumerate(self.weights):
            if w > mean:
                self.weights[i] = w - max(1, (w - mean) // 8)
            elif w < mean:
                self.weights[i] = w + max(1, (mean - w) // 16)
        if max(self.weights) > 1_000_000:
            self.weights = [max(1, w // 2) for w in self.weights]

    def projection_1_7(self) -> dict:
        return {"neutral": self.weights[0], "nonzero": sum(self.weights[1:])}

    def projection_1_3_4(self) -> dict:
        return {
            "origin": self.weights[0],
            "line": sum(self.weights[i] for i in (1, 2, 3)),
            "off_line": sum(self.weights[i] for i in (4, 5, 6, 7)),
        }

    def processing_pressure(self) -> dict:
        """Normalize 1|3|4 as conservative/coherent/exploratory control pressure."""
        p = self.projection_1_3_4()
        total = max(1, p["origin"] + p["line"] + p["off_line"])
        vals = {
            "conservative": p["origin"] / total,
            "coherent": p["line"] / total,
            "exploratory": p["off_line"] / total,
        }
        vals["dominant"] = max(("conservative", "coherent", "exploratory"), key=vals.get)
        return vals

    def line_scores(self) -> List[int]:
        return [sum(self.weights[i] for i in line) for line in FANO_LINES]

    def orientation_name(self) -> str:
        return ORIENTATION_NAMES[self.active_direction]

    def directive(self) -> str:
        return ORIENTATION_DIRECTIVES[self.active_direction]

    def choose_focus(self, texts: Sequence[str]) -> str:
        """Choose which available input receives attention under current orientation.

        This is deliberately lightweight and deterministic. It makes persistent
        Fano state causally affect downstream text/routing while leaving factual
        correctness to Evidence, sources and later checking.
        """
        clean = [str(t or "").strip() for t in texts if str(t or "").strip()]
        if not clean:
            return ""
        d = self.active_direction
        if d == 0:
            return clean[0]
        markers = _WORD_SETS.get(d, ())
        def score(t: str) -> tuple[int, int]:
            low = t.lower()
            marker_score = sum(low.count(w) for w in markers)
            # Direction 6 rewards lexical breadth; direction 7 rewards explicit uncertainty.
            breadth = len(set(re.findall(r"[a-z]{3,}", low))) if d == 6 else 0
            return marker_score, breadth
        best = max(range(len(clean)), key=lambda i: (score(clean[i]), -i))
        return clean[best]

    def integration_completion(self, texts: Sequence[str]) -> int:
        dirs = []
        for t in texts:
            d = direction_from_text(t)
            if d and d not in dirs:
                dirs.append(d)
            if len(dirs) >= 2:
                break
        return fano_completion(dirs[0], dirs[1]) if len(dirs) >= 2 else 0

    def summary(self) -> dict:
        lines = self.line_scores()
        pressure = self.processing_pressure()
        return {
            "step_count": self.step_count,
            "active_direction": self.active_direction,
            "orientation": self.orientation_name(),
            "directive": self.directive(),
            "weights": list(self.weights),
            "projection_1_7": self.projection_1_7(),
            "projection_1_3_4": self.projection_1_3_4(),
            "processing_pressure": pressure,
            "strongest_line": int(max(range(len(lines)), key=lambda i: lines[i])),
            "strongest_line_points": list(FANO_LINES[int(max(range(len(lines)), key=lambda i: lines[i]))]),
            "strongest_line_score": max(lines),
        }

    @classmethod
    def from_dict(cls, data: dict | None) -> "FanoJanusUnit":
        if not isinstance(data, dict):
            return cls()
        weights = data.get("weights")
        if not isinstance(weights, list) or len(weights) != 8:
            weights = [8, 1, 1, 1, 1, 1, 1, 1]
        clean = [max(1, int(x)) for x in weights]
        return cls(
            weights=clean,
            step_count=max(0, int(data.get("step_count") or 0)),
            active_direction=max(0, min(7, int(data.get("active_direction") or 0))),
        )
