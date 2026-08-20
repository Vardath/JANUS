"""Deterministic zero-API-cost Fano/JANUS 8-state substrate used inside each active core.

This is a functional computational implementation inspired by the audited JANUS/Fano
mathematics. It is not a physics or consciousness claim.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Iterable, List

# 000 is the distinguished/neutral state. The seven non-zero vectors of F2^3 are
# represented by integer labels 1..7.
FANO_LABELS = (0, 1, 2, 3, 4, 5, 6, 7)
FANO_LINES = (
    (1, 2, 3), (1, 4, 5), (1, 6, 7),
    (2, 4, 6), (2, 5, 7), (3, 4, 7), (3, 5, 6),
)


def xor3(a: int, b: int) -> int:
    return (a ^ b) & 0x7


@dataclass
class FanoJanusUnit:
    """Small persistent 8-state JANUS/Fano unit.

    `weights` are non-negative integer evidence/activation accumulators. State 0 is
    neutral/reference; 1..7 are the seven Fano directions. Inputs deterministically
    excite one or more directions, then a small reciprocal diffusion step lets
    evidence redistribute across the complete 8-state JANUS quotient without any
    external model call.
    """

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

    def _relax(self) -> None:
        total = sum(self.weights)
        # Integer mean-reversion toward the K8 neutral distribution, deliberately
        # weak so the unit retains history while avoiding unbounded divergence.
        mean = max(1, total // 8)
        for i, w in enumerate(self.weights):
            if w > mean:
                self.weights[i] = w - max(1, (w - mean) // 8)
            elif w < mean:
                self.weights[i] = w + max(1, (mean - w) // 16)
        scale = max(self.weights)
        if scale > 1_000_000:
            self.weights = [max(1, w // 2) for w in self.weights]

    def projection_1_7(self) -> dict:
        return {"neutral": self.weights[0], "nonzero": sum(self.weights[1:])}

    def projection_1_3_4(self) -> dict:
        # Canonical computational partition retained from the JANUS/Fano branch.
        return {
            "origin": self.weights[0],
            "line": sum(self.weights[i] for i in (1, 2, 3)),
            "off_line": sum(self.weights[i] for i in (4, 5, 6, 7)),
        }

    def line_scores(self) -> List[int]:
        return [sum(self.weights[i] for i in line) for line in FANO_LINES]

    def summary(self) -> dict:
        lines = self.line_scores()
        return {
            "step_count": self.step_count,
            "active_direction": self.active_direction,
            "weights": list(self.weights),
            "projection_1_7": self.projection_1_7(),
            "projection_1_3_4": self.projection_1_3_4(),
            "strongest_line": int(max(range(len(lines)), key=lambda i: lines[i])),
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
