from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from . import storage

CLOSED_STATES = {"implemented", "disapproved"}


def _default_path() -> Path:
    configured = os.getenv("JANUS_MAINTENANCE_REQUEST_FILE", "").strip()
    if configured:
        return Path(configured)
    db_path = os.getenv("JANUS_DB_PATH", "").strip()
    if db_path:
        parent = Path(db_path).expanduser().resolve().parent
        return parent / "janus_maintenance_requests.jsonl"
    return Path("data") / "janus_maintenance_requests.jsonl"


REQUEST_FILE = _default_path()


def _ensure_parent() -> None:
    REQUEST_FILE.parent.mkdir(parents=True, exist_ok=True)


def append_observation(request: dict[str, Any], *, created: bool) -> dict[str, Any]:
    """Append one JANUS-generated maintenance observation without overwriting history.

    The SQLite capability-request table remains the structured source of truth. This
    JSONL file is the durable human/Supervisor maintenance ledger. Repeated observations
    are intentionally appended so a later maintenance pass does not lose chronology.
    """
    _ensure_parent()
    entry = {
        "ledger_version": 1,
        "recorded_at": storage.now(),
        "request_id": int(request.get("id") or 0),
        "account_id": int(request.get("account_id") or 0),
        "fingerprint": str(request.get("fingerprint") or ""),
        "capability": str(request.get("capability") or "general"),
        "title": str(request.get("title") or "JANUS maintenance request"),
        "detail": str(request.get("detail") or ""),
        "evidence": str(request.get("evidence") or ""),
        "severity": str(request.get("severity") or "normal"),
        "state": str(request.get("state") or "awaiting_supervisor_review"),
        "occurrence_count": int(request.get("occurrence_count") or 1),
        "new_request": bool(created),
    }
    with REQUEST_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
    return entry


def read_entries() -> list[dict[str, Any]]:
    if not REQUEST_FILE.exists():
        return []
    out: list[dict[str, Any]] = []
    for raw in REQUEST_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except Exception:
            # Preserve malformed/manual notes rather than silently deleting them.
            out.append({"_raw": raw, "_malformed": True})
            continue
        if isinstance(value, dict):
            out.append(value)
    return out


def status() -> dict[str, Any]:
    entries = read_entries()
    return {
        "path": str(REQUEST_FILE),
        "exists": REQUEST_FILE.exists(),
        "append_only_generation": True,
        "entry_count": len(entries),
        "cleanup_rule": "Only maintenance reconciliation may remove entries, and only for implemented/disapproved requests.",
    }


def reconcile_closed() -> dict[str, Any]:
    """Remove only entries whose current request state is implemented/disapproved.

    This is the explicit maintenance cleanup operation. Deferred, pending, malformed,
    or unresolved entries are retained. The operation rewrites only during maintenance;
    JANUS generation itself always appends.
    """
    entries = read_entries()
    if not entries:
        return {"removed": 0, "kept": 0, "path": str(REQUEST_FILE)}

    rows = storage.rows("SELECT id,fingerprint,state FROM v2_capability_requests")
    by_id = {int(r["id"]): str(r.get("state") or "") for r in rows}
    by_fp = {str(r.get("fingerprint") or ""): str(r.get("state") or "") for r in rows if r.get("fingerprint")}

    kept_lines: list[str] = []
    removed = 0
    for entry in entries:
        if entry.get("_malformed"):
            kept_lines.append(str(entry.get("_raw") or ""))
            continue
        req_id = int(entry.get("request_id") or 0)
        fp = str(entry.get("fingerprint") or "")
        state = by_id.get(req_id) or by_fp.get(fp) or str(entry.get("state") or "")
        if state in CLOSED_STATES:
            removed += 1
            continue
        kept_lines.append(json.dumps(entry, ensure_ascii=False, sort_keys=True))

    _ensure_parent()
    temp = REQUEST_FILE.with_suffix(REQUEST_FILE.suffix + ".tmp")
    temp.write_text(("\n".join(kept_lines) + ("\n" if kept_lines else "")), encoding="utf-8")
    temp.replace(REQUEST_FILE)
    return {"removed": removed, "kept": len(kept_lines), "path": str(REQUEST_FILE)}


def instructions() -> str:
    return """JANUS MAINTENANCE REQUEST LEDGER PROCEDURE

1. Do not overwrite the JANUS-generated request ledger. JANUS generation is append-only.
2. Review every open capability/maintenance request against the current private repository and retained history.
3. Approve, disapprove, or defer each request independently. Implement only approved work.
4. Record every decision in server_v2/supervisor_decisions.json with request/fingerprint, reason, implementation state and version/commit.
5. Run the required server/Android/protocol/auth/maintenance regression gates for affected code.
6. Update CURRENT_CHECKPOINT.md and the current project-status/progress record.
7. After decisions are recorded, reconcile the request ledger: remove only IMPLEMENTED or DISAPPROVED request entries. Keep DEFERRED, PENDING and unresolved entries.
8. On deployed JANUS this reconciliation runs after supervisor_decisions.json is consumed. For a mounted maintenance environment it may also be run explicitly with:
   python -m server_v2.maintenance_request_file reconcile
9. Never delete an unresolved request merely because it is old or duplicated. Repeated observations are retained until that request is implemented or disapproved.
"""


def _main(argv: list[str]) -> int:
    command = (argv[1] if len(argv) > 1 else "instructions").strip().lower()
    if command in {"instructions", "help", "--help", "-h"}:
        print(instructions())
        return 0
    if command == "status":
        print(json.dumps(status(), indent=2, sort_keys=True))
        return 0
    if command == "reconcile":
        print(json.dumps(reconcile_closed(), indent=2, sort_keys=True))
        return 0
    if command == "print-open":
        for entry in read_entries():
            if entry.get("_malformed"):
                print(entry.get("_raw") or "")
                continue
            if str(entry.get("state") or "") not in CLOSED_STATES:
                print(json.dumps(entry, ensure_ascii=False, sort_keys=True))
        return 0
    print(f"Unknown command: {command}", file=sys.stderr)
    print(instructions(), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
