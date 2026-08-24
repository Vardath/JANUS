from __future__ import annotations

from typing import Any

from . import identity, storage
from .mind import HEMISPHERES, SPECIALISTS, mind
from .senses import SenseFrame
from .topology import FRONT_CORE, INTERFACE_CORE


def ingest(
    account_id: int,
    modality: str,
    source: str,
    content: str,
    *,
    salience: float = 0.6,
    uncertainty: float = 0.45,
    novelty: float = 0.5,
    metadata: dict[str, Any] | None = None,
    mode: str = "capability",
) -> dict[str, Any] | None:
    """Project a bounded capability event through the persistent 1|3|7 society.

    This performs deterministic JANUS state integration only. It never calls a
    language model, never generates a second user-facing answer, and never lets a
    capability result jump directly into Front. The typed SenseFrame is projected
    through all seven specialists, both hemispheres, Front, then Interface state.
    """
    text = " ".join(str(content or "").split())[:12000]
    if not text:
        return None
    aid = int(account_id)
    identity.ensure(aid)
    mind._states(aid)
    memories = storage.relevant_memories(aid, text, 6)
    frame = SenseFrame(
        modality=str(modality or "runtime")[:40],
        source=str(source or "capability")[:120],
        content=text,
        salience=max(0.0, min(1.0, float(salience))),
        uncertainty=max(0.0, min(1.0, float(uncertainty))),
        novelty=max(0.0, min(1.0, float(novelty))),
        metadata=dict(metadata or {}),
    )
    specialist_outputs: dict[str, dict[str, Any]] = {}
    evidence = text if frame.modality in {"file", "image", "audio", "web", "action_result"} else ""
    web_text = text if frame.modality == "web" else ""
    for name in SPECIALISTS:
        out = mind._specialist(name, frame, memories, evidence, web_text)
        specialist_outputs[name] = out
        mind._record_core(aid, name, f"{frame.modality}_sense", out["summary"], mode, out["appraisal"])
    left = mind._hemisphere(aid, "left_hemisphere", specialist_outputs)
    right = mind._hemisphere(aid, "right_hemisphere", specialist_outputs)
    mind._record_core(aid, "left_hemisphere", "capability_integration", left["summary"], mode, left["appraisal"])
    mind._record_core(aid, "right_hemisphere", "capability_integration", right["summary"], mode, right["appraisal"])
    front = mind._front(left, right, text)
    mind._record_core(aid, FRONT_CORE, "capability_appraisal", front["summary"], mode, front["appraisal"])
    interface_summary = (
        f"Interface registered a {frame.modality} capability result from {frame.source}; "
        f"Front posture={front['posture']}. No automatic outward action was taken."
    )
    mind._record_core(aid, INTERFACE_CORE, "capability_result", interface_summary, mode, front["appraisal"])
    return {
        "modality": frame.modality,
        "source": frame.source,
        "front_posture": front["posture"],
        "front_appraisal": front["appraisal"].as_dict(),
        "route_trace": [*SPECIALISTS, *HEMISPHERES, FRONT_CORE, INTERFACE_CORE],
        "model_calls": 0,
    }
