"""Forward-only routing policy for the JANUS 11-core society.

Ordinary cognition flows specialists -> hemispheres -> consensus -> interface.
Consensus/interface output is not recycled as the next primary topic. Cross-scale
feedback is tagged, compressed, and re-enters through specialist review only.
"""
from __future__ import annotations

from datetime import datetime, timezone


def _clip(text: str, limit: int = 420) -> str:
    clean = " ".join(str(text or "").split())
    return clean if len(clean) <= limit else clean[:limit] + "…"


def install(cycle) -> None:
    if getattr(cycle, "_forward_routing_policy_installed", False):
        return
    cycle._forward_routing_policy_installed = True

    specialists_left = {"evidence", "logic", "counterpoint"}
    specialists_right = {"context", "memory", "novelty"}

    def forward_route(sender: str, content: str) -> None:
        if sender in specialists_left:
            cycle.send(sender, "left_hemisphere", content, "specialist")
        elif sender in specialists_right:
            cycle.send(sender, "right_hemisphere", content, "specialist")
        elif sender == "safety":
            # Safety is advisory across integration, but does not create a loop.
            cycle.send(sender, "left_hemisphere", content, "safety")
            cycle.send(sender, "right_hemisphere", content, "safety")
            cycle.send(sender, "consensus", content, "safety")
        elif sender in {"left_hemisphere", "right_hemisphere"}:
            # Hemispheres do their distinct jobs independently; Consensus is the
            # only ordinary reconciliation point.
            cycle.send(sender, "consensus", content, "hemisphere")
        elif sender == "consensus":
            cycle._last_consensus = content
            cycle.send(sender, "interface", content, "consensus")
        elif sender == "interface":
            # Interface is a surface, not a new primary thinking topic.
            cycle._last_interface = content

    cycle._route_output = forward_route

    def accept_remote_summary(device_id, summary):
        clean = {
            "received_at": datetime.now(timezone.utc).isoformat(),
            "phase": str(summary.get("phase") or "unknown")[:32],
            "consensus": str(summary.get("consensus") or "")[:1000],
            "interface": str(summary.get("interface") or "")[:1000],
            "cycles": dict(summary.get("cycles") or {}),
        }
        cycle._remote_summaries[str(device_id)[:128]] = clean

        # Global/client integration is allowed, but only as explicitly tagged,
        # compressed feedback through specialist review. Never inject remote
        # Consensus/Interface directly into Consensus/Interface again.
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
