from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, asdict
from typing import Any

SPECIALISTS = ("evidence", "safety", "counterpoint", "context", "logic", "novelty", "memory")
HEMISPHERES = ("left_hemisphere", "right_hemisphere")
CORE_NAMES = (*SPECIALISTS, *HEMISPHERES, "front", "interface")
HOME_DIRECTIONS = {
    "evidence": 1,
    "safety": 2,
    "counterpoint": 3,
    "context": 4,
    "logic": 5,
    "novelty": 6,
    "memory": 7,
}
SENSE_MODALITIES = ("text", "image", "audio", "file", "web", "memory", "runtime", "peer", "action_result")


def _unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _signed(value: float) -> float:
    return max(-1.0, min(1.0, float(value)))


def _clip(value: str, limit: int = 900) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[:limit] + "…"


@dataclass
class Appraisal:
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

    def bounded(self) -> "Appraisal":
        self.confidence = _unit(self.confidence)
        self.valence = _signed(self.valence)
        for name in ("salience", "uncertainty", "novelty", "urgency", "familiarity", "risk", "opportunity", "conflict"):
            setattr(self, name, _unit(getattr(self, name)))
        return self

    def posture(self) -> str:
        self.bounded()
        if self.risk >= 0.8 and self.urgency >= 0.6:
            return "interrupt_or_warn"
        if self.conflict >= 0.7 or self.uncertainty >= 0.75:
            return "clarify_or_preserve_uncertainty"
        if self.opportunity >= 0.7 and self.risk <= 0.4:
            return "explore_or_act"
        if self.salience <= 0.25:
            return "defer_or_observe"
        return "respond_normally"

    def payload(self) -> dict[str, Any]:
        data = asdict(self.bounded())
        data["action_posture"] = self.posture()
        return data


@dataclass
class CoreState:
    cycles: int = 0
    last: str = ""
    appraisal: Appraisal | None = None

    def ensure_appraisal(self) -> Appraisal:
        if self.appraisal is None:
            self.appraisal = Appraisal()
        return self.appraisal


class LocalJanusSociety:
    """Persistent, deterministic Windows-local JANUS 11-core society.

    No network or model calls occur here. Raw capabilities are sensed only when the
    host client supplies them. Peer/global state is treated as a new ``peer`` sense
    and passes through all seven specialists before Left/Right/Front/Interface.
    """

    def __init__(self, storage_path: str | None = None):
        base = os.path.join(os.path.expanduser("~"), ".janus")
        self.storage_path = storage_path or os.path.join(base, "local_society_v1.json")
        self._lock = threading.RLock()
        self.phase = "wake"
        self.last_sense_at = 0
        self.cores = {name: CoreState(appraisal=Appraisal()) for name in CORE_NAMES}
        self.recent_senses: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        try:
            with open(self.storage_path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            self.phase = str(raw.get("phase") or "wake")
            self.last_sense_at = int(raw.get("last_sense_at") or 0)
            for name in CORE_NAMES:
                row = (raw.get("cores") or {}).get(name) or {}
                app = Appraisal(**{k: row.get("appraisal", {}).get(k, getattr(Appraisal(), k)) for k in asdict(Appraisal())})
                self.cores[name] = CoreState(int(row.get("cycles") or 0), str(row.get("last") or ""), app.bounded())
            self.recent_senses = list(raw.get("recent_senses") or [])[-24:]
        except Exception:
            pass

    def _save(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            payload = {
                "architecture": "1|3|7",
                "mechanical_flow": "7 -> 2 -> 1 -> 1",
                "phase": self.phase,
                "last_sense_at": self.last_sense_at,
                "cores": {
                    name: {
                        "cycles": state.cycles,
                        "last": state.last,
                        "appraisal": state.ensure_appraisal().payload(),
                    }
                    for name, state in self.cores.items()
                },
                "recent_senses": self.recent_senses[-24:],
            }
            tmp = self.storage_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
            os.replace(tmp, self.storage_path)
        except Exception:
            pass

    @staticmethod
    def _signals(content: str) -> dict[str, float]:
        t = str(content or "").lower()
        risk_words = ("danger", "unsafe", "risk", "harm", "leak", "breach", "crash", "error", "fail", "broken")
        opportunity_words = ("improve", "possible", "idea", "create", "build", "could", "opportunity", "explore", "new")
        conflict_words = ("but", "however", "conflict", "disagree", "contradict", "versus", "instead")
        urgency_words = ("urgent", "now", "immediately", "critical", "asap")
        positive_words = ("good", "like", "better", "success", "useful", "want", "help")
        negative_words = ("bad", "dislike", "worse", "failure", "harm", "problem", "wrong")
        positive = sum(1 for x in positive_words if x in t)
        negative = sum(1 for x in negative_words if x in t)
        return {
            "risk": min(1.0, sum(1 for x in risk_words if x in t) / 3.0),
            "opportunity": min(1.0, sum(1 for x in opportunity_words if x in t) / 3.0),
            "conflict": min(1.0, sum(1 for x in conflict_words if x in t) / 2.0),
            "urgency": min(1.0, sum(1 for x in urgency_words if x in t) / 2.0),
            "valence": _signed((positive - negative) / 4.0),
        }

    def _project(self, name: str, frame: dict[str, Any]) -> tuple[str, Appraisal]:
        content = _clip(frame["content"], 700)
        sig = self._signals(content)
        salience = _unit(frame["salience"])
        uncertainty = _unit(frame["uncertainty"])
        novelty = _unit(frame["novelty"])
        base = Appraisal(
            confidence=1.0 - uncertainty,
            valence=sig["valence"],
            salience=salience,
            uncertainty=uncertainty,
            novelty=novelty,
            urgency=sig["urgency"],
            familiarity=1.0 - novelty,
            risk=sig["risk"],
            opportunity=sig["opportunity"],
            conflict=sig["conflict"],
        )
        if name == "evidence":
            summary = f"Evidence sensed support/confidence needs in {frame['modality']}: {content}"
            base.confidence = max(base.confidence, 0.55 if content else 0.2)
        elif name == "safety":
            summary = f"Safety sensed valence, welfare and boundaries: {content}"
            base.risk = max(base.risk, 0.2 if frame["source"] == "peer" else 0.0)
        elif name == "counterpoint":
            summary = f"Counterpoint sensed consequence, conflict and failure possibilities: {content}"
            base.conflict = max(base.conflict, uncertainty * 0.55)
        elif name == "context":
            summary = f"Context sensed pattern, relationship and environment: {content}"
            base.familiarity = max(base.familiarity, 0.45)
        elif name == "logic":
            summary = f"Logic sensed constraints, model and causal structure: {content}"
            base.confidence = (base.confidence + (1.0 - base.conflict)) / 2.0
        elif name == "novelty":
            summary = f"Novelty sensed alternatives, imagination and direction: {content}"
            base.opportunity = max(base.opportunity, novelty * 0.75)
        else:
            summary = f"Memory compared the sense with retained continuity: {content}"
            base.familiarity = max(base.familiarity, 0.6 if self.recent_senses else 0.35)
        return _clip(summary, 900), base.bounded()

    @staticmethod
    def _merge(appraisals: list[Appraisal]) -> Appraisal:
        if not appraisals:
            return Appraisal()
        n = float(len(appraisals))
        return Appraisal(
            confidence=sum(x.confidence for x in appraisals) / n,
            valence=sum(x.valence for x in appraisals) / n,
            salience=max(x.salience for x in appraisals),
            uncertainty=max(x.uncertainty for x in appraisals),
            novelty=max(x.novelty for x in appraisals),
            urgency=max(x.urgency for x in appraisals),
            familiarity=sum(x.familiarity for x in appraisals) / n,
            risk=max(x.risk for x in appraisals),
            opportunity=max(x.opportunity for x in appraisals),
            conflict=max(x.conflict for x in appraisals),
        ).bounded()

    def sense(self, modality: str, source: str, content: str, *, salience: float = 0.5, uncertainty: float = 0.5, novelty: float = 0.5) -> dict[str, Any]:
        if modality not in SENSE_MODALITIES:
            raise ValueError(f"unsupported sensory modality: {modality}")
        frame = {
            "modality": modality,
            "source": _clip(source, 80),
            "content": _clip(content, 1600),
            "salience": _unit(salience),
            "uncertainty": _unit(uncertainty),
            "novelty": _unit(novelty),
            "created_at": int(time.time()),
        }
        with self._lock:
            self.last_sense_at = frame["created_at"]
            self.recent_senses.append(frame)
            self.recent_senses = self.recent_senses[-24:]

            projections: dict[str, tuple[str, Appraisal]] = {}
            for name in SPECIALISTS:
                summary, appraisal = self._project(name, frame)
                state = self.cores[name]
                state.cycles += 1
                state.last = summary
                state.appraisal = appraisal
                projections[name] = (summary, appraisal)

            apps = [projections[name][1] for name in SPECIALISTS]
            left_app = self._merge(apps)
            left_app.confidence = _unit((left_app.confidence + (1.0 - left_app.conflict)) / 2.0)
            left_summary = "Left constrained the complete seven-core field for explicit consistency and causal structure."
            left = self.cores["left_hemisphere"]
            left.cycles += 1; left.last = left_summary; left.appraisal = left_app

            right_app = self._merge(apps)
            right_app.novelty = max(right_app.novelty, right_app.opportunity)
            right_summary = "Right expanded the complete seven-core field through association, context, alternatives and imagination."
            right = self.cores["right_hemisphere"]
            right.cycles += 1; right.last = right_summary; right.appraisal = right_app

            front_app = self._merge([left_app, right_app])
            front_summary = f"Front appraised both hemispheres; posture={front_app.posture()}; source={frame['source']}; modality={modality}."
            front = self.cores["front"]
            front.cycles += 1; front.last = front_summary; front.appraisal = front_app

            interface_app = self._merge([front_app])
            interface_summary = f"Interface prepared bounded expression/action; posture={interface_app.posture()}."
            interface = self.cores["interface"]
            interface.cycles += 1; interface.last = interface_summary; interface.appraisal = interface_app
            self._save()
            return self.snapshot()

    def pulse(self) -> dict[str, Any]:
        return self.sense("runtime", "windows-local", "bounded deterministic local maintenance pulse", salience=0.2, uncertainty=0.1, novelty=0.1)

    def ingest_peer(self, server: dict[str, Any]) -> dict[str, Any]:
        if not server:
            return self.snapshot()
        content = " ".join(
            part for part in (
                str(server.get("front") or server.get("consensus") or "").strip(),
                str(server.get("interface") or "").strip(),
            ) if part
        )
        if not content:
            content = f"global phase={server.get('phase','unknown')} topology={server.get('conceptual_topology','1|3|7')}"
        peer_app = server.get("front_appraisal") or {}
        return self.sense(
            "peer", "global-janus", content,
            salience=float(peer_app.get("salience", 0.55) or 0.55),
            uncertainty=float(peer_app.get("uncertainty", 0.4) or 0.4),
            novelty=float(peer_app.get("novelty", 0.4) or 0.4),
        )

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            cores = {
                name: {
                    "cycles": state.cycles,
                    "last": state.last,
                    "home_direction": HOME_DIRECTIONS.get(name, 0),
                    "appraisal": state.ensure_appraisal().payload(),
                }
                for name, state in self.cores.items()
            }
            return {
                "architecture": "1|3|7",
                "mechanical_flow": "7 -> 2 -> 1 -> 1",
                "core_count": 11,
                "phase": self.phase,
                "last_sense_at": self.last_sense_at,
                "cycles": {name: row["cycles"] for name, row in cores.items()},
                "core_summaries": {name: row["last"] for name, row in cores.items()},
                "front": cores["front"]["last"],
                "front_appraisal": cores["front"]["appraisal"],
                "interface": cores["interface"]["last"],
                "interface_appraisal": cores["interface"]["appraisal"],
                "cores": cores,
                "sense_modalities": list(SENSE_MODALITIES),
                "background_external_api_calls": 0,
            }
