"""JANUS local sleep/wake cycle.

Keeps the seven local research cores active without consuming external API budget.
Only local state transitions, message passing, lightweight scoring, consolidation,
and queueing happen here. External/cloud work must be explicitly dispatched elsewhere.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional
import threading
import time

CORE_NAMES = (
    "evidence",
    "logic",
    "counterpoint",
    "context",
    "memory",
    "safety",
    "novelty",
)

@dataclass
class CoreMessage:
    sender: str
    recipient: str
    kind: str
    content: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass
class CoreState:
    name: str
    awake: bool = False
    cycle_count: int = 0
    thoughts: List[str] = field(default_factory=list)
    inbox: List[CoreMessage] = field(default_factory=list)
    last_cycle_at: Optional[str] = None

class JanusSleepCycle:
    """Zero-API-cost local seven-core sleep/wake cycle."""

    def __init__(self, wake_seconds: int = 300, sleep_seconds: int = 600,
                 local_thinker: Optional[Callable[[CoreState, List[CoreMessage]], str]] = None) -> None:
        self.wake_seconds = max(10, int(wake_seconds))
        self.sleep_seconds = max(10, int(sleep_seconds))
        self.local_thinker = local_thinker or self._default_local_thinker
        self.cores: Dict[str, CoreState] = {name: CoreState(name=name) for name in CORE_NAMES}
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._phase = "sleep"

    @property
    def phase(self) -> str:
        return self._phase

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="janus-sleep-cycle", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def status(self) -> dict:
        return {
            "phase": self._phase,
            "wake_seconds": self.wake_seconds,
            "sleep_seconds": self.sleep_seconds,
            "external_api_budget_used": 0,
            "cores": {
                name: {
                    "awake": core.awake,
                    "cycle_count": core.cycle_count,
                    "pending_messages": len(core.inbox),
                    "last_cycle_at": core.last_cycle_at,
                }
                for name, core in self.cores.items()
            },
        }

    def _run(self) -> None:
        while not self._stop.is_set():
            self._enter_phase("wake")
            self._run_wake_window()
            if self._stop.is_set():
                break
            self._enter_phase("sleep")
            self._run_sleep_window()

    def _enter_phase(self, phase: str) -> None:
        self._phase = phase
        awake = phase == "wake"
        for core in self.cores.values():
            core.awake = awake

    def _run_wake_window(self) -> None:
        deadline = time.monotonic() + self.wake_seconds
        while time.monotonic() < deadline and not self._stop.is_set():
            for core in self.cores.values():
                incoming = list(core.inbox)
                core.inbox.clear()
                thought = self.local_thinker(core, incoming)
                if thought:
                    core.thoughts.append(thought)
                    core.thoughts[:] = core.thoughts[-64:]
                    self._broadcast(core.name, "reflection", thought)
                core.cycle_count += 1
                core.last_cycle_at = datetime.now(timezone.utc).isoformat()
            time.sleep(5)

    def _run_sleep_window(self) -> None:
        for core in self.cores.values():
            core.thoughts[:] = core.thoughts[-16:]
        deadline = time.monotonic() + self.sleep_seconds
        while time.monotonic() < deadline and not self._stop.is_set():
            time.sleep(5)

    def _broadcast(self, sender: str, kind: str, content: str) -> None:
        for recipient, target in self.cores.items():
            if recipient != sender:
                target.inbox.append(CoreMessage(sender=sender, recipient=recipient, kind=kind, content=content))

    @staticmethod
    def _default_local_thinker(core: CoreState, incoming: List[CoreMessage]) -> str:
        # Deliberately not an LLM: deterministic local processing only.
        if not incoming:
            return f"{core.name}: idle self-check complete"
        themes = sorted({msg.sender for msg in incoming})
        sample = incoming[-1].content[:180].replace("\n", " ")
        return f"{core.name}: reviewed {len(incoming)} peer messages from {', '.join(themes)}; latest={sample}"

janus_sleep_cycle = JanusSleepCycle()
