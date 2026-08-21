"""Low-duty server processing policy for the JANUS 11-core society.

The main interface remains continuously available. During the society's nominal
rest phase, the ten background cores still perform deterministic/Fano processing
at a slower cadence. This layer never invokes an external model API.
"""
from __future__ import annotations

import os
import time
import types

from src.janus_sleep_cycle import (
    SPECIALIST_CORES,
    HEMISPHERE_CORES,
    CONSENSUS_CORE,
    INTERFACE_CORE,
)


def install(cycle):
    rest_seconds=max(10,int(os.environ.get("JANUS_CORE_REST_BACKGROUND_SECONDS","30")))
    cycle.rest_background_seconds=rest_seconds
    cycle.core_cycle_api_calls=0

    def low_duty_sleep_window(self):
        for x in self.cores.values():
            x.thoughts=x.thoughts[-16:]
        self.cores[INTERFACE_CORE].awake=True
        self.checkpoint(True)
        deadline=time.monotonic()+self.sleep_seconds
        next_background=time.monotonic()
        while time.monotonic()<deadline and not self._stop.is_set():
            with self._lock:
                now=time.monotonic()
                if now>=next_background:
                    # A complete low-duty community pass. Awake here means
                    # actively processing this turn, not an external API call.
                    for stage in (SPECIALIST_CORES,HEMISPHERE_CORES,(CONSENSUS_CORE,)):
                        for name in stage:
                            core=self.cores[name]
                            core.awake=True
                            self._cycle_core(name)
                            core.awake=False
                    next_background=now+rest_seconds
                # Consensus and safety routing can leave work for the interface.
                # Service it immediately; the interface never sleeps.
                if self.cores[INTERFACE_CORE].inbox:
                    self._cycle_core(INTERFACE_CORE)
            self.checkpoint()
            time.sleep(5)

    cycle._run_sleep_window=types.MethodType(low_duty_sleep_window,cycle)

    original_status=cycle.status
    def status_with_policy():
        result=original_status()
        result["rest_background_seconds"]=rest_seconds
        result["core_cycle_api_calls"]=0
        result["rest_policy"]="low-duty processing; interface continuous"
        for name,core in (result.get("cores") or {}).items():
            core["available"]=True
            if name==INTERFACE_CORE:
                core["processing_mode"]="continuous"
            elif result.get("phase")=="wake":
                core["processing_mode"]="full-rate"
            else:
                core["processing_mode"]="low-duty"
        return result
    cycle.status=status_with_policy

    original_compact=cycle.compact_summary
    def compact_with_policy():
        result=original_compact()
        result["rest_background_seconds"]=rest_seconds
        result["core_cycle_api_calls"]=0
        return result
    cycle.compact_summary=compact_with_policy
    return cycle
