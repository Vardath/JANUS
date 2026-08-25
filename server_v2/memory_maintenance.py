from __future__ import annotations

from typing import Any

from . import storage

TRACE_MAX_AGE = 14 * 86400
WORKING_MAX_AGE = 60 * 86400
EPISODIC_REVIEW_AGE = 365 * 86400


def maintain(account_id: int, *, now_ts: int | None = None, dry_run: bool = False) -> dict[str, Any]:
    """Conservative account-local memory housekeeping.

    Core memories are protected. Episodic memories are not automatically deleted here.
    Only stale, low-salience trace/working memories with little retrieval history are
    eligible for automatic deletion. This is maintenance during cognitive rest, not
    an active thought cycle.
    """
    aid = int(account_id)
    ts = int(now_ts if now_ts is not None else storage.now())
    rows = storage.rows(
        "SELECT id,tier,kind,content,salience,access_count,created_at,updated_at FROM v2_memories WHERE account_id=? ORDER BY updated_at ASC",
        (aid,),
    )
    delete_ids: list[int] = []
    review_ids: list[int] = []
    protected = 0
    retained = 0
    for row in rows:
        tier = str(row.get("tier") or "working")
        age = max(0, ts - int(row.get("updated_at") or row.get("created_at") or ts))
        salience = float(row.get("salience") or 0.0)
        access = int(row.get("access_count") or 0)
        if tier == "core":
            protected += 1
            continue
        if tier == "episodic":
            if age >= EPISODIC_REVIEW_AGE and salience < 0.25 and access == 0:
                review_ids.append(int(row["id"]))
            else:
                retained += 1
            continue
        stale_trace = tier == "trace" and age >= TRACE_MAX_AGE and salience < 0.35 and access <= 1
        stale_working = tier == "working" and age >= WORKING_MAX_AGE and salience < 0.30 and access == 0
        if stale_trace or stale_working:
            delete_ids.append(int(row["id"]))
        else:
            retained += 1
    if delete_ids and not dry_run:
        with storage.db() as c:
            c.executemany("DELETE FROM v2_memories WHERE account_id=? AND id=?", [(aid, mid) for mid in delete_ids])
    result = {
        "account_id": aid,
        "scanned": len(rows),
        "protected_core": protected,
        "retained": retained,
        "deleted_low_value": 0 if dry_run else len(delete_ids),
        "delete_candidates": len(delete_ids),
        "episodic_review_candidates": len(review_ids),
        "automatic_episodic_deletion": False,
        "automatic_core_deletion": False,
        "active_thought": False,
    }
    if not dry_run and (delete_ids or review_ids):
        storage.add_event(
            aid,
            "memory",
            "rest_memory_maintenance",
            f"Rest maintenance scanned {len(rows)} memories; deleted {len(delete_ids)} stale low-value trace/working memories; {len(review_ids)} old low-value episodic memories were flagged for review but retained; core memories protected.",
            mode="rest",
        )
    return result
