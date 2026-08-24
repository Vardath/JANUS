from __future__ import annotations

import os
import threading
import time
from typing import Any

from . import storage
from .mind import mind


class RuntimePersistence:
    """Durable checkpointing for each account's private 11-core runtime state.

    Legacy ``consensus`` rows are accepted by ``mind.restore_profile`` and mapped to
    canonical ``front`` state. Checkpoints themselves always persist exactly the
    eleven canonical cores; compatibility aliases are read-only and never become a
    twelfth mind.
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

    def restore_all(self) -> dict[str, int]:
        restored_profiles = 0
        restored_cores = 0
        for account in storage.rows("SELECT id FROM v2_accounts ORDER BY id"):
            aid = int(account["id"])
            rows = storage.rows(
                "SELECT core_name,cycle_count,last_public_summary,last_active_at FROM v2_runtime_core_state WHERE account_id=?",
                (aid,),
            )
            if rows:
                mind.restore_profile(aid, rows)
                restored_profiles += 1
                # Report canonical core count even while a legacy consensus row may
                # still exist prior to the first new checkpoint.
                names = {"front" if str(row.get("core_name") or "") == "consensus" else str(row.get("core_name") or "") for row in rows}
                restored_cores += len(names)
        return {"profiles": restored_profiles, "cores": restored_cores}

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
            # Once canonical Front has been checkpointed, remove any stale legacy
            # alias so the database contains eleven and only eleven runtime cores.
            c.execute("DELETE FROM v2_runtime_core_state WHERE account_id=? AND core_name='consensus'", (int(account_id),))
        return len(rows)

    def checkpoint_all(self) -> dict[str, int]:
        profiles = 0
        cores = 0
        for account in storage.rows("SELECT id FROM v2_accounts ORDER BY id"):
            count = self.checkpoint_account(int(account["id"]))
            profiles += 1
            cores += count
        return {"profiles": profiles, "cores": cores}

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
