"""JANUS zero-API-cost persistent 11-core sleep/wake runtime.

Architecture:
- 7 specialist cores: evidence, logic, counterpoint, context, memory, safety, novelty
- 2 hemispheres: left_hemisphere, right_hemisphere
- 1 consensus core: consensus
- 1 interface core: interface

All eleven cores are active software processes inside the runtime. They may message
individual peers, named groups, or broadcast. The background loop deliberately
performs no paid/cloud model calls. Runtime state is checkpointed to the persistent
JANUS SQLite database (normally /data/janus.sqlite3 on Render) so server restarts do
not reset core cycle counts, outputs, pending messages, consensus or interface state.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional
import json
import os
import sqlite3
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

DB_PATH = os.environ.get("JANUS_DB_PATH", "/data/janus.sqlite3")
CHECKPOINT_SECONDS = max(10, int(os.environ.get("JANUS_CORE_CHECKPOINT_SECONDS", "30")))

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
    """Zero-API-cost persistent eleven-core communicating sleep/wake cycle."""

    def __init__(self, wake_seconds: int = 300, sleep_seconds: int = 600,
                 local_thinker: Optional[Callable[[CoreState, List[CoreMessage]], str]] = None) -> None:
        self.wake_seconds = max(10, int(wake_seconds))
        self.sleep_seconds = max(10, int(sleep_seconds))
        self.local_thinker = local_thinker or self._default_local_thinker
        self.cores: Dict[str, CoreState] = {name: CoreState(name=name) for name in CORE_NAMES}
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._phase = "sleep"
        self._phase_started_at = time.time()
        self._lock = threading.RLock()
        self._last_consensus = ""
        self._last_interface = ""
        self._remote_summaries: Dict[str, dict] = {}
        self._last_checkpoint = 0.0
        self._persistence_ready = False
        self._init_persistence()
        self._restore_state()

    def _db(self):
        c = sqlite3.connect(DB_PATH, timeout=10)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        return c

    def _init_persistence(self) -> None:
        try:
            os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
            with self._db() as c:
                c.executescript("""
                CREATE TABLE IF NOT EXISTS janus_core_runtime_state (
                    core_name TEXT PRIMARY KEY,
                    cycle_count INTEGER NOT NULL DEFAULT 0,
                    awake INTEGER NOT NULL DEFAULT 0,
                    thoughts_json TEXT NOT NULL DEFAULT '[]',
                    inbox_json TEXT NOT NULL DEFAULT '[]',
                    last_cycle_at TEXT,
                    last_output TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS janus_core_runtime_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS janus_core_remote_summary (
                    device_id TEXT PRIMARY KEY,
                    summary_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """)
            self._persistence_ready = True
        except Exception:
            self._persistence_ready = False

    def _restore_state(self) -> None:
        if not self._persistence_ready:
            return
        try:
            with self._db() as c:
                for row in c.execute("SELECT * FROM janus_core_runtime_state"):
                    name = str(row["core_name"])
                    if name not in self.cores:
                        continue
                    core = self.cores[name]
                    core.cycle_count = int(row["cycle_count"] or 0)
                    core.awake = bool(row["awake"])
                    core.last_cycle_at = row["last_cycle_at"]
                    core.last_output = str(row["last_output"] or "")
                    try:
                        core.thoughts = [str(x) for x in json.loads(row["thoughts_json"] or "[]")][-64:]
                    except Exception:
                        core.thoughts = []
                    try:
                        restored = []
                        for item in json.loads(row["inbox_json"] or "[]")[-128:]:
                            if isinstance(item, dict):
                                restored.append(CoreMessage(
                                    sender=str(item.get("sender") or "unknown")[:64],
                                    recipient=name,
                                    kind=str(item.get("kind") or "restored")[:64],
                                    content=str(item.get("content") or "")[:4000],
                                    group=(str(item.get("group"))[:64] if item.get("group") is not None else None),
                                    created_at=str(item.get("created_at") or datetime.now(timezone.utc).isoformat()),
                                ))
                        core.inbox = restored
                    except Exception:
                        core.inbox = []
                meta = {r["key"]: r["value"] for r in c.execute("SELECT key,value FROM janus_core_runtime_meta")}
                self._phase = str(meta.get("phase") or "sleep")
                self._last_consensus = str(meta.get("last_consensus") or "")
                self._last_interface = str(meta.get("last_interface") or "")
                try:
                    self._phase_started_at = float(meta.get("phase_started_at") or time.time())
                except Exception:
                    self._phase_started_at = time.time()
                for row in c.execute("SELECT device_id,summary_json FROM janus_core_remote_summary"):
                    try:
                        self._remote_summaries[str(row["device_id"])] = json.loads(row["summary_json"])
                    except Exception:
                        pass
        except Exception:
            pass

    def checkpoint(self, force: bool = False) -> bool:
        if not self._persistence_ready:
            return False
        now_mono = time.monotonic()
        if not force and now_mono - self._last_checkpoint < CHECKPOINT_SECONDS:
            return True
        stamp = datetime.now(timezone.utc).isoformat()
        try:
            with self._lock, self._db() as c:
                for name, core in self.cores.items():
                    inbox_json = json.dumps([asdict(m) for m in core.inbox[-128:]], separators=(",", ":"))
                    thoughts_json = json.dumps(core.thoughts[-64:], separators=(",", ":"))
                    c.execute("""INSERT INTO janus_core_runtime_state
                        (core_name,cycle_count,awake,thoughts_json,inbox_json,last_cycle_at,last_output,updated_at)
                        VALUES(?,?,?,?,?,?,?,?)
                        ON CONFLICT(core_name) DO UPDATE SET
                        cycle_count=excluded.cycle_count,awake=excluded.awake,thoughts_json=excluded.thoughts_json,
                        inbox_json=excluded.inbox_json,last_cycle_at=excluded.last_cycle_at,last_output=excluded.last_output,
                        updated_at=excluded.updated_at""",
                        (name, core.cycle_count, 1 if core.awake else 0, thoughts_json, inbox_json,
                         core.last_cycle_at, core.last_output[-4000:], stamp))
                for key, value in {
                    "phase": self._phase,
                    "phase_started_at": str(self._phase_started_at),
                    "last_consensus": self._last_consensus[-4000:],
                    "last_interface": self._last_interface[-4000:],
                }.items():
                    c.execute("""INSERT INTO janus_core_runtime_meta(key,value,updated_at) VALUES(?,?,?)
                               ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at""",
                              (key, value, stamp))
                for device_id, summary in list(self._remote_summaries.items())[-100:]:
                    c.execute("""INSERT INTO janus_core_remote_summary(device_id,summary_json,updated_at) VALUES(?,?,?)
                               ON CONFLICT(device_id) DO UPDATE SET summary_json=excluded.summary_json,updated_at=excluded.updated_at""",
                              (device_id, json.dumps(summary, separators=(",", ":")), stamp))
            self._last_checkpoint = now_mono
            return True
        except Exception:
            return False

    @property
    def phase(self) -> str:
        return self._phase

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="janus-11core-cycle", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self.checkpoint(force=True)

    def send(self, sender: str, recipient: str, content: str, kind: str = "peer") -> None:
        if sender not in self.cores or recipient not in self.cores:
            return
        with self._lock:
            self.cores[recipient].inbox.append(CoreMessage(sender, recipient, kind, str(content)[:4000]))

    def send_group(self, sender: str, group: str, content: str, kind: str = "group") -> None:
        members = CORE_GROUPS.get(group, set())
        with self._lock:
            for recipient in members:
                if recipient != sender and recipient in self.cores:
                    self.cores[recipient].inbox.append(CoreMessage(sender, recipient, kind, str(content)[:4000], group=group))

    def broadcast(self, sender: str, content: str, kind: str = "broadcast") -> None:
        self.send_group(sender, "all", content, kind)

    def accept_remote_summary(self, device_id: str, summary: dict) -> None:
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
        self.checkpoint()

    def compact_summary(self) -> dict:
        with self._lock:
            return {
                "architecture": "7 specialists + 2 hemispheres + 1 consensus + 1 interface",
                "phase": self._phase,
                "consensus": self._last_consensus,
                "interface": self._last_interface,
                "cycles": {name: core.cycle_count for name, core in self.cores.items()},
                "persistent": self._persistence_ready,
            }

    def status(self) -> dict:
        with self._lock:
            return {
                "architecture": "11-core",
                "topology": "7 -> 2 -> 1 -> 1",
                "core_count": 11,
                "phase": self._phase,
                "wake_seconds": self.wake_seconds,
                "sleep_seconds": self.sleep_seconds,
                "external_api_budget_used": 0,
                "persistent_storage": self._persistence_ready,
                "storage_backend": "sqlite-render-disk" if self._persistence_ready else "memory-only",
                "database_path": DB_PATH,
                "checkpoint_seconds": CHECKPOINT_SECONDS,
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
            self._enter_phase("wake")
            self._run_wake_window()
            if self._stop.is_set():
                break
            self._enter_phase("sleep")
            self._run_sleep_window()
        self.checkpoint(force=True)

    def _enter_phase(self, phase: str) -> None:
        self._phase = phase
        self._phase_started_at = time.time()
        awake = phase == "wake"
        with self._lock:
            for core in self.cores.values():
                core.awake = awake
        self.checkpoint(force=True)

    def _run_wake_window(self) -> None:
        deadline = time.monotonic() + self.wake_seconds
        while time.monotonic() < deadline and not self._stop.is_set():
            with self._lock:
                for name in CORE_NAMES:
                    core = self.cores[name]
                    incoming = list(core.inbox)
                    core.inbox.clear()
                    thought = self.local_thinker(core, incoming)
                    if thought:
                        core.thoughts.append(thought)
                        core.thoughts[:] = core.thoughts[-64:]
                        core.last_output = thought
                        self._route_output(core.name, thought)
                    core.cycle_count += 1
                    core.last_cycle_at = datetime.now(timezone.utc).isoformat()
            self.checkpoint()
            time.sleep(5)

    def _run_sleep_window(self) -> None:
        with self._lock:
            for core in self.cores.values():
                core.thoughts[:] = core.thoughts[-16:]
        self.checkpoint(force=True)
        deadline = time.monotonic() + self.sleep_seconds
        while time.monotonic() < deadline and not self._stop.is_set():
            self.checkpoint()
            time.sleep(5)

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
