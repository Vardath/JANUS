"""Forward-only routing policy for the JANUS 11-core society.

Ordinary cognition flows specialists -> hemispheres -> consensus -> interface.
Consensus/interface output is not recycled as the next primary topic. Cross-scale
feedback is tagged, compressed, and re-enters through specialist review only.
"""
from __future__ import annotations

from datetime import datetime, timezone
import os


def _clip(text: str, limit: int = 420) -> str:
    clean = " ".join(str(text or "").split())
    return clean if len(clean) <= limit else clean[:limit] + "…"


def install(cycle) -> None:
    if getattr(cycle, "_forward_routing_policy_installed", False):
        return
    cycle._forward_routing_policy_installed = True

    specialists_left = {"evidence", "logic", "counterpoint"}
    specialists_right = {"context", "memory", "novelty"}
    remote_cap = max(8, int(os.environ.get("JANUS_REMOTE_DEVICE_SUMMARY_CAP", "100")))

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
        # Keep persistent restore state aligned with the in-memory bound.
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
