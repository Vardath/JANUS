from __future__ import annotations

import json
from pathlib import Path

from . import diagnostics, storage

SEED_FILE = Path(__file__).with_name("pending_maintenance_seed.json")


def apply_pending_seed() -> dict[str, object]:
    """Persist the repo-authored pending maintenance request into JANUS-owned DB storage.

    The seed is idempotent because diagnostics.record_request deduplicates on the
    capability/title/detail fingerprint. The owner account is resolved as the first
    account after persistent-data migration, matching the existing maintenance owner
    fallback when no explicit owner profile is configured.
    """
    if not SEED_FILE.exists():
        return {"applied": False, "reason": "seed_missing"}
    try:
        payload = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"applied": False, "reason": "seed_invalid"}
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
    return {
        "applied": True,
        "request_id": int(request.get("id") or 0),
        "title": str(request.get("title") or payload.get("title") or ""),
        "state": str(request.get("state") or "awaiting_supervisor_review"),
    }
