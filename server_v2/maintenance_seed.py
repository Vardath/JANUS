from __future__ import annotations

import json
from pathlib import Path

from . import diagnostics, storage

SEED_FILE = Path(__file__).with_name("pending_maintenance_seed.json")


def apply_pending_seed() -> dict[str, object]:
    """Persist one repo-authored pending maintenance request into JANUS-owned storage.

    A separate seed-sync key prevents server restarts from being counted as repeated
    occurrences. After initial seeding, only genuine JANUS re-detection/reopening uses
    the normal capability-request occurrence counter.
    """
    if not SEED_FILE.exists():
        return {"applied": False, "reason": "seed_missing"}
    try:
        payload = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"applied": False, "reason": "seed_invalid"}

    seed_key = str(payload.get("seed_key") or "").strip()
    if not seed_key:
        return {"applied": False, "reason": "seed_key_missing"}

    with storage.db() as c:
        c.execute(
            "CREATE TABLE IF NOT EXISTS v2_maintenance_seed_sync(seed_key TEXT PRIMARY KEY, request_id INTEGER NOT NULL, applied_at INTEGER NOT NULL)"
        )
        existing = c.execute(
            "SELECT request_id FROM v2_maintenance_seed_sync WHERE seed_key=?",
            (seed_key,),
        ).fetchone()
    if existing:
        return {"applied": False, "reason": "already_applied", "request_id": int(existing["request_id"])}

    owner = storage.one("SELECT * FROM v2_accounts ORDER BY id ASC LIMIT 1")
    if owner is None:
        return {"applied": False, "reason": "owner_account_missing"}

    request = diagnostics.record_request(
        int(owner["id"]),
        str(payload.get("capability") or "maintenance_governance"),
        str(payload.get("title") or "Pending maintenance architecture request"),
        str(payload.get("detail") or "Review the maintenance architecture."),
        evidence=str(payload.get("evidence") or ""),
        severity=str(payload.get("severity") or "normal"),
    )
    request_id = int(request.get("id") or 0)
    with storage.db() as c:
        c.execute(
            "INSERT OR IGNORE INTO v2_maintenance_seed_sync(seed_key,request_id,applied_at) VALUES(?,?,?)",
            (seed_key, request_id, storage.now()),
        )
    return {
        "applied": True,
        "request_id": request_id,
        "title": str(request.get("title") or payload.get("title") or ""),
        "state": str(request.get("state") or "awaiting_supervisor_review"),
    }
