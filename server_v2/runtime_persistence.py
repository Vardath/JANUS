from __future__ import annotations

import json
import os
import threading
import time
from typing import Any

from . import storage
from .mind import mind


class RuntimePersistence:
    """Durable checkpointing for outer and nested JANUS runtime state.

    The canonical outer runtime still persists exactly eleven top-level cores. When
    the production mind supports recursive JANUS cores, each of those eleven also
    gets one durable JSON checkpoint containing its internal seven-position Fano
    state, peer-revision counters and bounded AI counsel/conclusion.
    """

    def __init__(self):
        self._running = False
        self._thread: threading.Thread | None = None
        self.interval = max(10, int(os.getenv("JANUS_CORE_CHECKPOINT_SECONDS", "30")))

    def init_schema(self) -> None:
        with storage.db() as c:
            c.execute(
                """CREATE TABLE IF NOT EXISTS v2_runtime_core_state(
                  account_id INTEGER NOT NULL REFERENCES v2_accounts(id) ON DELETE CASCADE,
                  core_name TEXT NOT NULL,
                  cycle_count INTEGER NOT NULL DEFAULT 0,
                  last_public_summary TEXT NOT NULL DEFAULT '',
                  last_active_at INTEGER NOT NULL DEFAULT 0,
                  updated_at INTEGER NOT NULL,
                  PRIMARY KEY(account_id,core_name)
                )"""
            )
            c.execute(
                """CREATE TABLE IF NOT EXISTS v2_recursive_core_state(
                  account_id INTEGER NOT NULL REFERENCES v2_accounts(id) ON DELETE CASCADE,
                  core_name TEXT NOT NULL,
                  state_json TEXT NOT NULL DEFAULT '{}',
                  updated_at INTEGER NOT NULL,
                  PRIMARY KEY(account_id,core_name)
                )"""
            )

    def _restore_recursive(self, aid: int) -> int:
        if not hasattr(mind, "_recursive_states"):
            return 0
        rows = storage.rows(
            "SELECT core_name,state_json FROM v2_recursive_core_state WHERE account_id=?",
            (int(aid),),
        )
        if not rows:
            return 0
        states = mind._recursive_states(int(aid))
        restored = 0
        for row in rows:
            name = str(row.get("core_name") or "")
            state = states.get(name)
            if state is None:
                continue
            try:
                data = json.loads(str(row.get("state_json") or "{}"))
                weights = data.get("weights")
                if isinstance(weights, list) and len(weights) >= 8:
                    state.weights = [max(1, int(v)) for v in weights[:8]]
                state.active_direction = int(data.get("active_direction") or 0)
                state.revision_count = int(data.get("revision_count") or 0)
                state.peer_turn_count = int(data.get("peer_turn_count") or 0)
                state.ai_last = str(data.get("ai_last") or "")[:900]
                state.last_conclusion = str(data.get("conclusion") or "")[:1600]
                faculties = data.get("faculties")
                if isinstance(faculties, dict):
                    state.last_faculties = {int(k): str(v)[:800] for k, v in faculties.items() if str(k).isdigit()}
                restored += 1
            except Exception:
                continue
        return restored

    def restore_all(self) -> dict[str, int]:
        restored_profiles = 0
        restored_cores = 0
        restored_recursive = 0
        for account in storage.rows("SELECT id FROM v2_accounts ORDER BY id"):
            aid = int(account["id"])
            rows = storage.rows(
                "SELECT core_name,cycle_count,last_public_summary,last_active_at FROM v2_runtime_core_state WHERE account_id=?",
                (aid,),
            )
            if rows:
                mind.restore_profile(aid, rows)
                restored_profiles += 1
                names = {"front" if str(row.get("core_name") or "") == "consensus" else str(row.get("core_name") or "") for row in rows}
                restored_cores += len(names)
            restored_recursive += self._restore_recursive(aid)
        return {"profiles": restored_profiles, "cores": restored_cores, "recursive_cores": restored_recursive}

    def _checkpoint_recursive(self, account_id: int, ts: int) -> int:
        if not hasattr(mind, "_recursive_states"):
            return 0
        states = mind._recursive_states(int(account_id))
        count = 0
        with storage.db() as c:
            for name, state in states.items():
                try:
                    payload = json.dumps(state.snapshot(), ensure_ascii=False, separators=(",", ":"))
                except Exception:
                    continue
                c.execute(
                    """INSERT INTO v2_recursive_core_state(account_id,core_name,state_json,updated_at)
                       VALUES(?,?,?,?)
                       ON CONFLICT(account_id,core_name) DO UPDATE SET
                         state_json=excluded.state_json,updated_at=excluded.updated_at""",
                    (int(account_id), str(name), payload[:24000], int(ts)),
                )
                count += 1
        return count

    def checkpoint_account(self, account_id: int) -> int:
        exported = mind.export_profile(int(account_id))
        rows = [row for row in exported if str(row.get("core_name") or "") != "consensus"]
        ts = storage.now()
        with storage.db() as c:
            for row in rows:
                c.execute(
                    """INSERT INTO v2_runtime_core_state(account_id,core_name,cycle_count,last_public_summary,last_active_at,updated_at)
                       VALUES(?,?,?,?,?,?)
                       ON CONFLICT(account_id,core_name) DO UPDATE SET
                         cycle_count=excluded.cycle_count,
                         last_public_summary=excluded.last_public_summary,
                         last_active_at=excluded.last_active_at,
                         updated_at=excluded.updated_at""",
                    (int(account_id), row["core_name"], int(row["cycle_count"]), str(row["last_public_summary"])[:4000], int(row["last_active_at"]), ts),
                )
            c.execute("DELETE FROM v2_runtime_core_state WHERE account_id=? AND core_name='consensus'", (int(account_id),))
        self._checkpoint_recursive(int(account_id), ts)
        return len(rows)

    def checkpoint_all(self) -> dict[str, int]:
        profiles = 0
        cores = 0
        recursive_cores = 0
        for account in storage.rows("SELECT id FROM v2_accounts ORDER BY id"):
            aid = int(account["id"])
            count = self.checkpoint_account(aid)
            profiles += 1
            cores += count
            if hasattr(mind, "_recursive_states"):
                recursive_cores += len(mind._recursive_states(aid))
        return {"profiles": profiles, "cores": cores, "recursive_cores": recursive_cores}

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="janus-v2-runtime-persistence", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        try:
            self.checkpoint_all()
        except Exception:
            pass

    def _loop(self) -> None:
        while self._running:
            deadline = time.time() + self.interval
            while self._running and time.time() < deadline:
                time.sleep(min(2.0, max(0.25, deadline - time.time())))
            if not self._running:
                break
            try:
                self.checkpoint_all()
            except Exception:
                pass


runtime_persistence = RuntimePersistence()
