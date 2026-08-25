from __future__ import annotations

from typing import Any

from . import identity, storage
from .recursive_mind import mind
from .senses import SenseFrame
from .topology import CORE_NAMES, FRONT_CORE, INTERFACE_CORE
from .mind import SPECIALISTS, HEMISPHERES


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
    """Integrate a typed sense through eleven recursive JANUS cores with zero model calls."""
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
    evidence = text if frame.modality in {"file", "image", "audio", "web", "action_result"} else ""
    web_text = text if frame.modality == "web" else ""

    specialist_outputs: dict[str, dict[str, Any]] = {}
    recursive: dict[str, dict[str, Any]] = {}
    for name in SPECIALISTS:
        out = mind._specialist(name, frame, memories, evidence, web_text)
        recursive[name] = mind._run_recursive(aid, name, frame.content + " | " + out["summary"], out["appraisal"])
        out["summary"] = (out["summary"] + " " + recursive[name]["conclusion"])[:4800]
        specialist_outputs[name] = out

    first = {name: recursive[name]["conclusion"] for name in SPECIALISTS}
    for name in SPECIALISTS:
        peers = [(peer, summary) for peer, summary in first.items() if peer != name]
        recursive[name] = mind._run_recursive(aid, name, frame.content, specialist_outputs[name]["appraisal"], peers)
        specialist_outputs[name]["summary"] = (specialist_outputs[name]["summary"] + " Revised: " + recursive[name]["conclusion"])[:5200]
        mind._record_core(aid, name, f"recursive_{frame.modality}_sense", specialist_outputs[name]["summary"], mode, specialist_outputs[name]["appraisal"])

    left = mind._hemisphere(aid, "left_hemisphere", specialist_outputs)
    right = mind._hemisphere(aid, "right_hemisphere", specialist_outputs)
    specialist_peers = [(name, recursive[name]["conclusion"]) for name in SPECIALISTS]
    recursive["left_hemisphere"] = mind._run_recursive(aid, "left_hemisphere", left["summary"], left["appraisal"], specialist_peers)
    recursive["right_hemisphere"] = mind._run_recursive(aid, "right_hemisphere", right["summary"], right["appraisal"], specialist_peers)
    left["summary"] = (left["summary"] + " " + recursive["left_hemisphere"]["conclusion"])[:6200]
    right["summary"] = (right["summary"] + " " + recursive["right_hemisphere"]["conclusion"])[:6200]
    mind._record_core(aid, "left_hemisphere", "recursive_capability_integration", left["summary"], mode, left["appraisal"])
    mind._record_core(aid, "right_hemisphere", "recursive_capability_integration", right["summary"], mode, right["appraisal"])

    front = mind._front(left, right, text)
    recursive[FRONT_CORE] = mind._run_recursive(aid, FRONT_CORE, front["summary"], front["appraisal"], [
        ("left_hemisphere", recursive["left_hemisphere"]["conclusion"]),
        ("right_hemisphere", recursive["right_hemisphere"]["conclusion"]),
    ])
    front["summary"] = (front["summary"] + " " + recursive[FRONT_CORE]["conclusion"])[:7600]
    mind._record_core(aid, FRONT_CORE, "recursive_capability_appraisal", front["summary"], mode, front["appraisal"])

    recursive[INTERFACE_CORE] = mind._run_recursive(aid, INTERFACE_CORE, front["summary"], front["appraisal"], [
        (FRONT_CORE, recursive[FRONT_CORE]["conclusion"]),
        ("left_hemisphere", recursive["left_hemisphere"]["conclusion"]),
        ("right_hemisphere", recursive["right_hemisphere"]["conclusion"]),
    ])
    interface_summary = (
        f"Interface recursive JANUS core registered a {frame.modality} result from {frame.source}; "
        f"Front posture={front['posture']}. No automatic outward action was taken. "
        + recursive[INTERFACE_CORE]["conclusion"]
    )
    mind._record_core(aid, INTERFACE_CORE, "recursive_capability_result", interface_summary[:4000], mode, front["appraisal"])
    return {
        "modality": frame.modality,
        "source": frame.source,
        "front_posture": front["posture"],
        "front_appraisal": front["appraisal"].as_dict(),
        "route_trace": [*SPECIALISTS, *HEMISPHERES, FRONT_CORE, INTERFACE_CORE],
        "recursive_core_engine": True,
        "recursive_core_count": len(CORE_NAMES),
        "model_calls": 0,
    }
