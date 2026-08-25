from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

from . import storage


def _enabled() -> bool:
    return os.getenv("JANUS_MAINTENANCE_GITHUB_MIRROR", "0").strip().lower() in {"1", "true", "yes", "on"}


def _repo() -> str:
    return os.getenv("JANUS_MAINTENANCE_GITHUB_REPO", "Vardath/JANUS-privatebuild").strip()


def _issue_number() -> int:
    try:
        return max(1, int(os.getenv("JANUS_MAINTENANCE_GITHUB_ISSUE", "1") or 1))
    except Exception:
        return 1


def _token() -> str:
    return os.getenv("JANUS_MAINTENANCE_GITHUB_TOKEN", "").strip()


def init_schema() -> None:
    with storage.db() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS v2_maintenance_issue_mirror(
              account_id INTEGER NOT NULL,
              fingerprint TEXT NOT NULL,
              occurrence_count INTEGER NOT NULL DEFAULT 0,
              mirrored_at INTEGER NOT NULL,
              PRIMARY KEY(account_id,fingerprint)
            )
            """
        )


def status() -> dict[str, Any]:
    token_present = bool(_token())
    repo = _repo()
    return {
        "enabled": _enabled(),
        "configured": bool(_enabled() and token_present and repo and _issue_number()),
        "repository": repo,
        "issue_number": _issue_number(),
        "token_present": token_present,
        "permission_intent": "GitHub Issues read/write only; no Contents/source-code write permission",
        "canonical_store": "Render SQLite + append-only JSONL ledger",
    }


def _clean(text: str, limit: int) -> str:
    value = str(text or "")
    # Never mirror obvious credential material even into the private Supervisor inbox.
    value = re.sub(r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s]+", r"\1[REDACTED]", value)
    value = re.sub(r"(?i)((?:api[_ -]?key|token|password|secret)\s*[:=]\s*)[^\s,;]+", r"\1[REDACTED]", value)
    value = " ".join(value.split())
    return value[:limit]


def _comment(request: dict[str, Any]) -> str:
    return "\n".join([
        "### JANUS maintenance observation",
        "",
        f"- Request ID: `{int(request.get('id') or 0)}`",
        f"- Fingerprint: `{_clean(request.get('fingerprint') or '', 80)}`",
        f"- Capability: `{_clean(request.get('capability') or 'general', 120)}`",
        f"- Severity: `{_clean(request.get('severity') or 'normal', 20)}`",
        f"- State: `{_clean(request.get('state') or 'awaiting_supervisor_review', 80)}`",
        f"- Occurrences: `{int(request.get('occurrence_count') or 1)}`",
        f"- Updated: `{int(request.get('updated_at') or storage.now())}`",
        "",
        f"**{_clean(request.get('title') or 'JANUS capability request', 240)}**",
        "",
        _clean(request.get('detail') or 'JANUS reported a maintenance/capability gap.', 5000),
        "",
        "Canonical request state remains on the JANUS Render persistent store. This private issue is a Supervisor-readable mirror only. JANUS has no source-code authority through this path.",
    ])


def _post_comment(body: str) -> None:
    token = _token()
    if not (_enabled() and token):
        raise RuntimeError("maintenance GitHub mirror is not configured")
    repo = _repo()
    if not repo or "/" not in repo:
        raise RuntimeError("invalid maintenance GitHub repository")
    url = f"https://api.github.com/repos/{repo}/issues/{_issue_number()}/comments"
    payload = json.dumps({"body": body}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "JANUS-maintenance-supervisor-mirror",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            if int(getattr(response, "status", 0) or 0) not in {200, 201}:
                raise RuntimeError(f"GitHub maintenance mirror returned HTTP {getattr(response, 'status', 0)}")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"GitHub maintenance mirror returned HTTP {exc.code}") from exc


def mirror_request(request: dict[str, Any]) -> dict[str, Any]:
    """Append a request observation once per occurrence count.

    Failure is intentionally non-fatal: Render SQLite/JSONL remain authoritative.
    """
    if not _enabled():
        return {"mirrored": False, "reason": "disabled"}
    if not _token():
        return {"mirrored": False, "reason": "token_missing"}
    init_schema()
    aid = int(request.get("account_id") or 0)
    fp = str(request.get("fingerprint") or "").strip()
    occurrence = max(1, int(request.get("occurrence_count") or 1))
    if not aid or not fp:
        return {"mirrored": False, "reason": "identity_missing"}
    row = storage.one(
        "SELECT occurrence_count FROM v2_maintenance_issue_mirror WHERE account_id=? AND fingerprint=?",
        (aid, fp),
    )
    if row and int(row["occurrence_count"] or 0) >= occurrence:
        return {"mirrored": False, "reason": "already_current"}
    try:
        _post_comment(_comment(request))
    except Exception as exc:
        return {"mirrored": False, "reason": "post_failed", "error": _clean(str(exc), 240)}
    with storage.db() as c:
        c.execute(
            """
            INSERT INTO v2_maintenance_issue_mirror(account_id,fingerprint,occurrence_count,mirrored_at)
            VALUES(?,?,?,?)
            ON CONFLICT(account_id,fingerprint) DO UPDATE SET
              occurrence_count=excluded.occurrence_count,
              mirrored_at=excluded.mirrored_at
            """,
            (aid, fp, occurrence, storage.now()),
        )
    return {"mirrored": True, "occurrence_count": occurrence}


def mirror_open_requests() -> dict[str, int]:
    """Backfill all currently unresolved requests when the server starts/restarts."""
    if not (_enabled() and _token()):
        return {"mirrored": 0, "skipped": 0, "failed": 0}
    init_schema()
    rows = storage.rows(
        "SELECT * FROM v2_capability_requests WHERE state NOT IN ('implemented','disapproved') ORDER BY account_id,id ASC"
    )
    mirrored = skipped = failed = 0
    for item in rows:
        result = mirror_request(dict(item))
        if result.get("mirrored"):
            mirrored += 1
        elif result.get("reason") == "post_failed":
            failed += 1
        else:
            skipped += 1
    return {"mirrored": mirrored, "skipped": skipped, "failed": failed}
