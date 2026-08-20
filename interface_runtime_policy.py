"""Always-available interface policy for the JANUS 11-core runtime.

The interface core remains awake while the other ten cores may sleep. During
society sleep it consumes any queued consensus messages immediately, preserving
latest-state continuity without forcing specialist/hemisphere cycles to run.
"""
from __future__ import annotations

from datetime import datetime, timezone
import time

from src.janus_sleep_cycle import INTERFACE_CORE


def install(cycle):
    if getattr(cycle, "_interface_always_on_installed", False):
        return cycle
    cycle._interface_always_on_installed = True

    def enter_phase(phase):
        cycle._phase = phase
        with cycle._lock:
            for name, core in cycle.cores.items():
                core.awake = phase == "wake" or name == INTERFACE_CORE
        cycle.checkpoint(True)

    def service_interface_once():
        with cycle._lock:
            core = cycle.cores[INTERFACE_CORE]
            core.awake = True
            if not core.inbox:
                return False
            incoming = list(core.inbox)
            core.inbox.clear()
            thought = cycle._think(core, incoming)
            core.thoughts.append(thought)
            core.thoughts = core.thoughts[-64:]
            core.last_output = thought
            core.cycle_count += 1
            core.last_cycle_at = datetime.now(timezone.utc).isoformat()
            cycle._route_output(INTERFACE_CORE, thought)
            return True

    def run_sleep_window():
        with cycle._lock:
            for name, core in cycle.cores.items():
                core.thoughts = core.thoughts[-(64 if name == INTERFACE_CORE else 16):]
                core.awake = name == INTERFACE_CORE
        cycle.checkpoint(True)
        deadline = time.monotonic() + cycle.sleep_seconds
        while time.monotonic() < deadline and not cycle._stop.is_set():
            if service_interface_once():
                cycle.checkpoint()
            else:
                cycle.checkpoint()
            time.sleep(5)

    original_status = cycle.status

    def status():
        data = original_status()
        data["interface_policy"] = "always_available"
        data["interface_awake"] = True
        data["society_may_rest"] = True
        data["answer_policy"] = "interface answers from latest synchronized state; other cores update asynchronously"
        if INTERFACE_CORE in data.get("cores", {}):
            data["cores"][INTERFACE_CORE]["awake"] = True
        return data

    cycle._enter_phase = enter_phase
    cycle._run_sleep_window = run_sleep_window
    cycle.service_interface_once = service_interface_once
    cycle.status = status
    cycle.cores[INTERFACE_CORE].awake = True
    cycle.checkpoint(True)
    return cycle
