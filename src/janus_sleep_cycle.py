"""JANUS zero-API-cost 11-core sleep/wake runtime.

Architecture:
- 7 specialist cores: evidence, logic, counterpoint, context, memory, safety, novelty
- 2 hemispheres: left_hemisphere, right_hemisphere
- 1 consensus core: consensus
- 1 interface core: interface

All eleven cores are active software processes inside the runtime. They may message
individual peers, named groups, or broadcast. This local loop deliberately performs
no paid/cloud model calls; external model use is dispatched elsewhere.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, Iterable, List, Optional
import threading
import time

SPECIALIST_CORES = (
    "evidence", "logic", "counterpoint", "context", "memory", "safety", "novelty",
)
HEMISPHERE_CORES = ("left_hemisphere", "right_hemisphere")
CONSENSUS_CORE = "consensus"
INTERFACE_CORE = "interface"
CORE_NAMES = SPECIALIST_CORES + HEMISPHERE_CORES + (CONSENSUS_CORE, INTERFACE_CORE)

CORE_GROUPS = {
    "specialists": set(SPECIALIST_CORES),
    "left": {"evidence", "logic", "counterpoint", "left_hemisphere"},
    "right": {"context", "memory", "novelty", "right_hemisphere"},
    "safety": {"safety", "left_hemisphere", "right_hemisphere", "consensus"},
    "hemispheres": set(HEMISPHERE_CORES),
    "integration": {"left_hemisphere", "right_hemisphere", "consensus", "interface"},
    "all": set(CORE_NAMES),
}

@dataclass
class CoreMessage:
    sender: str
    recipient: str
    kind: str
    content: str
    group: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass
class CoreState:
    name: str
    awake: bool = False
    cycle_count: int = 0
    thoughts: List[str] = field(default_factory=list)
    inbox: List[CoreMessage] = field(default_factory=list)
    last_cycle_at: Optional[str] = None
    last_output: str = ""

class JanusSleepCycle:
    """Zero-API-cost eleven-core communicating sleep/wake cycle."""

    def __init__(self, wake_seconds: int = 300, sleep_seconds: int = 600,
                 local_thinker: Optional[Callable[[CoreState, List[CoreMessage]], str]] = None) -> None:
        self.wake_seconds = max(10, int(wake_seconds))
        self.sleep_seconds = max(10, int(sleep_seconds))
        self.local_thinker = local_thinker or self._default_local_thinker
        self.cores: Dict[str, CoreState] = {name: CoreState(name=name) for name in CORE_NAMES}
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._phase = "sleep"
        self._lock = threading.RLock()
        self._last_consensus = ""
        self._last_interface = ""
        self._remote_summaries: Dict[str, dict] = {}

    @property
    def phase(self) -> str: return self._phase

    def start(self) -> None:
        if self._thread and self._thread.is_alive(): return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="janus-11core-cycle", daemon=True)
        self._thread.start()

    def stop(self) -> None: self._stop.set()

    def send(self, sender: str, recipient: str, content: str, kind: str = "peer") -> None:
        if sender not in self.cores or recipient not in self.cores: return
        with self._lock:
            self.cores[recipient].inbox.append(CoreMessage(sender, recipient, kind, content))

    def send_group(self, sender: str, group: str, content: str, kind: str = "group") -> None:
        members = CORE_GROUPS.get(group, set())
        with self._lock:
            for recipient in members:
                if recipient != sender and recipient in self.cores:
                    self.cores[recipient].inbox.append(CoreMessage(sender, recipient, kind, content, group=group))

    def broadcast(self, sender: str, content: str, kind: str = "broadcast") -> None:
        self.send_group(sender, "all", content, kind)

    def accept_remote_summary(self, device_id: str, summary: dict) -> None:
        """Accept a compact authenticated client-core summary; never executes remote code."""
        clean = {
            "received_at": datetime.now(timezone.utc).isoformat(),
            "phase": str(summary.get("phase") or "unknown")[:32],
            "consensus": str(summary.get("consensus") or "")[:1000],
            "interface": str(summary.get("interface") or "")[:1000],
            "cycles": dict(summary.get("cycles") or {}),
        }
        with self._lock:
            self._remote_summaries[str(device_id)[:128]] = clean
            self.send("interface", "consensus", f"client-sync {device_id}: {clean['consensus']}", "client_sync")

    def compact_summary(self) -> dict:
        with self._lock:
            return {
                "architecture": "7 specialists + 2 hemispheres + 1 consensus + 1 interface",
                "phase": self._phase,
                "consensus": self._last_consensus,
                "interface": self._last_interface,
                "cycles": {name: core.cycle_count for name, core in self.cores.items()},
            }

    def status(self) -> dict:
        with self._lock:
            return {
                "architecture": "11-core",
                "core_count": 11,
                "phase": self._phase,
                "wake_seconds": self.wake_seconds,
                "sleep_seconds": self.sleep_seconds,
                "external_api_budget_used": 0,
                "last_consensus": self._last_consensus,
                "last_interface": self._last_interface,
                "remote_clients": len(self._remote_summaries),
                "groups": {k: sorted(v) for k, v in CORE_GROUPS.items()},
                "cores": {name: {
                    "awake": core.awake,
                    "cycle_count": core.cycle_count,
                    "pending_messages": len(core.inbox),
                    "last_cycle_at": core.last_cycle_at,
                    "last_output": core.last_output[-300:],
                } for name, core in self.cores.items()},
            }

    def _run(self) -> None:
        while not self._stop.is_set():
            self._enter_phase("wake"); self._run_wake_window()
            if self._stop.is_set(): break
            self._enter_phase("sleep"); self._run_sleep_window()

    def _enter_phase(self, phase: str) -> None:
        self._phase = phase; awake = phase == "wake"
        with self._lock:
            for core in self.cores.values(): core.awake = awake

    def _run_wake_window(self) -> None:
        deadline = time.monotonic() + self.wake_seconds
        while time.monotonic() < deadline and not self._stop.is_set():
            with self._lock:
                for name in CORE_NAMES:
                    core = self.cores[name]
                    incoming = list(core.inbox); core.inbox.clear()
                    thought = self.local_thinker(core, incoming)
                    if thought:
                        core.thoughts.append(thought); core.thoughts[:] = core.thoughts[-64:]
                        core.last_output = thought
                        self._route_output(core.name, thought)
                    core.cycle_count += 1
                    core.last_cycle_at = datetime.now(timezone.utc).isoformat()
            time.sleep(5)

    def _run_sleep_window(self) -> None:
        with self._lock:
            for core in self.cores.values(): core.thoughts[:] = core.thoughts[-16:]
        deadline = time.monotonic() + self.sleep_seconds
        while time.monotonic() < deadline and not self._stop.is_set(): time.sleep(5)

    def _route_output(self, sender: str, content: str) -> None:
        if sender in {"evidence", "logic", "counterpoint"}:
            self.send(sender, "left_hemisphere", content, "specialist")
        elif sender in {"context", "memory", "novelty"}:
            self.send(sender, "right_hemisphere", content, "specialist")
        elif sender == "safety":
            self.send_group(sender, "integration", content, "safety")
        elif sender in HEMISPHERE_CORES:
            other = "right_hemisphere" if sender == "left_hemisphere" else "left_hemisphere"
            self.send(sender, other, content, "cross_hemisphere")
            self.send(sender, "consensus", content, "hemisphere")
        elif sender == "consensus":
            self._last_consensus = content
            self.send(sender, "interface", content, "consensus")
            self.send_group(sender, "hemispheres", content, "feedback")
        elif sender == "interface":
            self._last_interface = content
            self.send(sender, "consensus", content, "interface_feedback")

    @staticmethod
    def _default_local_thinker(core: CoreState, incoming: List[CoreMessage]) -> str:
        if not incoming:
            return f"{core.name}: idle self-check complete"
        senders = sorted({m.sender for m in incoming})
        snippets = [m.content[:120].replace("\n", " ") for m in incoming[-4:]]
        joined = " | ".join(snippets)
        if core.name == "left_hemisphere":
            return f"left_hemisphere: analytic synthesis of {len(incoming)} inputs from {', '.join(senders)}; {joined}"
        if core.name == "right_hemisphere":
            return f"right_hemisphere: contextual/associative synthesis of {len(incoming)} inputs from {', '.join(senders)}; {joined}"
        if core.name == "consensus":
            return f"consensus: integrated reading of {len(incoming)} inputs from {', '.join(senders)}; {joined}"
        if core.name == "interface":
            return f"interface: user-facing state derived from consensus; {joined}"
        return f"{core.name}: reviewed {len(incoming)} peer inputs from {', '.join(senders)}; {joined}"

janus_sleep_cycle = JanusSleepCycle()
