"""Forward-only routing plus operational Fano processing policy for JANUS.

Ordinary cognition flows specialists -> hemispheres -> consensus -> interface.
Consensus/interface output is not recycled as the next primary topic. Fano state
controls attention/integration style, but never creates factual evidence.
"""
from __future__ import annotations

from datetime import datetime, timezone
import os


def _clip(text: str, limit: int = 420) -> str:
    clean = " ".join(str(text or "").split())
    return clean if len(clean) <= limit else clean[:limit] + "…"


_ROLE_ACTION = {
    "evidence": "separate recorded support from inference",
    "logic": "test consistency, constraints and causal structure",
    "counterpoint": "challenge the current view with alternatives and failure modes",
    "context": "relate the topic to goals, environment and prior context",
    "memory": "compare the topic with retained history and unfinished work",
    "safety": "check privacy, security, risk and epistemic boundaries",
    "novelty": "seek an unusual but testable connection",
    "left_hemisphere": "synthesize Evidence, Logic and Counterpoint",
    "right_hemisphere": "synthesize Context, Memory and Novelty",
    "consensus": "integrate the hemispheres while preserving real disagreement",
    "interface": "surface a concise externalizable shared state",
}


def install(cycle) -> None:
    if getattr(cycle, "_forward_routing_policy_installed", False):
        return
    cycle._forward_routing_policy_installed = True

    specialists_left = {"evidence", "logic", "counterpoint"}
    specialists_right = {"context", "memory", "novelty"}
    integration = {"left_hemisphere", "right_hemisphere", "consensus", "interface"}
    remote_cap = max(8, int(os.environ.get("JANUS_REMOTE_DEVICE_SUMMARY_CAP", "100")))

    # Fano is now causally upstream of the output: it selects which available
    # input receives attention, supplies a processing directive, and at
    # integration stages completes two distinct incoming Fano points by XOR.
    # The completion is a small bias, not a truth signal or hard override.
    def semantic_think(core, incoming):
        texts = [m.content for m in incoming] or [core.last_output or core.name]
        core.fano.ingest(texts, core.name)
        completion = core.fano.integration_completion(texts) if core.name in integration else 0
        if completion:
            core.fano.bias(completion, 2)
        state = core.fano.summary()
        p = state["projection_1_3_4"]
        pressure = state["processing_pressure"]
        focus = _clip(core.fano.choose_focus(texts), 520) or "retained/maintenance state"
        senders = sorted({m.sender for m in incoming})
        peer = f" from {', '.join(senders)}" if senders else ""
        completion_note = f"; line-completion=d{completion}" if completion else ""
        return (
            f"{core.name}: {_ROLE_ACTION.get(core.name, 'process assigned work')}; "
            f"Fano d{state['active_direction']}={state['orientation']}; "
            f"control={state['directive']}; "
            f"pressure={pressure['dominant']} "
            f"({pressure['conservative']:.2f}/{pressure['coherent']:.2f}/{pressure['exploratory']:.2f}); "
            f"1|3|4={p['origin']}|{p['line']}|{p['off_line']}"
            f"{completion_note}; focus={focus}; processed {len(incoming)} peer inputs{peer}"
        )

    cycle._think = semantic_think

    def forward_route(sender: str, content: str) -> None:
        if sender in specialists_left:
            cycle.send(sender, "left_hemisphere", content, "specialist")
        elif sender in specialists_right:
            cycle.send(sender, "right_hemisphere", content, "specialist")
        elif sender == "safety":
            cycle.send(sender, "left_hemisphere", content, "safety")
            cycle.send(sender, "right_hemisphere", content, "safety")
            cycle.send(sender, "consensus", content, "safety")
        elif sender in {"left_hemisphere", "right_hemisphere"}:
            cycle.send(sender, "consensus", content, "hemisphere")
        elif sender == "consensus":
            cycle._last_consensus = content
            cycle.send(sender, "interface", content, "consensus")
        elif sender == "interface":
            cycle._last_interface = content

    cycle._route_output = forward_route

    def _trim_remote_summaries() -> None:
        if len(cycle._remote_summaries) <= remote_cap:
            return
        ordered = sorted(
            cycle._remote_summaries.items(),
            key=lambda kv: str((kv[1] or {}).get("received_at") or ""),
        )
        stale = [key for key, _ in ordered[: max(0, len(ordered) - remote_cap)]]
        for key in stale:
            cycle._remote_summaries.pop(key, None)
        db = getattr(cycle, "_db", None)
        if callable(db) and stale:
            try:
                with db() as c:
                    c.executemany("DELETE FROM janus_core_remote_summary WHERE device_id=?", [(x,) for x in stale])
            except Exception:
                pass

    def accept_remote_summary(device_id, summary):
        clean = {
            "received_at": datetime.now(timezone.utc).isoformat(),
            "phase": str(summary.get("phase") or "unknown")[:32],
            "consensus": str(summary.get("consensus") or "")[:1000],
            "interface": str(summary.get("interface") or "")[:1000],
            "cycles": dict(summary.get("cycles") or {}),
        }
        cycle._remote_summaries[str(device_id)[:128]] = clean
        _trim_remote_summaries()

        combined = _clip(
            "client feedback; consensus=" + clean["consensus"] +
            "; interface=" + clean["interface"],
            520,
        )
        if combined.strip(" ;"):
            cycle.send("interface", "context", "[feedback-only] " + combined, "client_feedback")
            cycle.send("interface", "counterpoint", "[feedback-only] check for disagreement/novelty: " + combined, "client_feedback")
        cycle.checkpoint()

    cycle.accept_remote_summary = accept_remote_summary
