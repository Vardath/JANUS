"""Autonomous global JANUS attachment retention and storage auditing.

The auditor is deliberately zero-paid-API-cost. It uses persisted attachment
metadata, cached extraction, duplicate detection, age and storage pressure to
make bounded keep/delete decisions. Decisions are logged and summarized back
through JANUS specialist cores so housekeeping is observable runtime activity.
"""
from __future__ import annotations

import os
import re
import sqlite3
import threading
import time
from pathlib import Path
from typing import Optional

from fastapi import Header, HTTPException, Request
from pydantic import BaseModel

import auth

DB_PATH = Path(os.getenv("JANUS_DB_PATH", "/data/janus.sqlite3"))
FILE_ROOT = Path(os.getenv("JANUS_FILE_DIR", "/data/janus_files"))
STALE_SECONDS = max(86400, int(os.getenv("JANUS_FILE_STALE_SECONDS", str(7 * 86400))))
SOFT_STORAGE_BYTES = max(8 * 1024 * 1024, int(os.getenv("JANUS_FILE_STORAGE_SOFT_BYTES", str(256 * 1024 * 1024))))
HARD_STORAGE_BYTES = max(SOFT_STORAGE_BYTES, int(os.getenv("JANUS_FILE_STORAGE_HARD_BYTES", str(512 * 1024 * 1024))))
AUDIT_INTERVAL_SECONDS = max(900, int(os.getenv("JANUS_FILE_AUDIT_INTERVAL_SECONDS", str(6 * 3600))))
WORKER_POLL_SECONDS = max(60, min(900, AUDIT_INTERVAL_SECONDS // 4))
TEMP_NAME_RE = re.compile(r"(?:^|[._ -])(tmp|temp|copy|backup|old|test|debug|scratch)(?:[._ -]|$)", re.I)

_worker_lock = threading.Lock()
_worker_started = False
_last_result: dict = {"ran": False, "reason": "not yet audited"}


class PinRequest(BaseModel):
    pinned: bool


def _db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    return c


def _table_exists(c: sqlite3.Connection, name: str) -> bool:
    return c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def _ensure_column(c: sqlite3.Connection, name: str, declaration: str) -> None:
    cols = {r[1] for r in c.execute("PRAGMA table_info(janus_files)")}
    if name not in cols:
        c.execute(f"ALTER TABLE janus_files ADD COLUMN {declaration}")


def init_retention_schema() -> None:
    FILE_ROOT.mkdir(parents=True, exist_ok=True)
    with _db() as c:
        if not _table_exists(c, "janus_files"):
            return
        _ensure_column(c, "last_touched_at", "last_touched_at INTEGER NOT NULL DEFAULT 0")
        _ensure_column(c, "last_referenced_at", "last_referenced_at INTEGER NOT NULL DEFAULT 0")
        _ensure_column(c, "pinned", "pinned INTEGER NOT NULL DEFAULT 0")
        _ensure_column(c, "last_audited_at", "last_audited_at INTEGER NOT NULL DEFAULT 0")
        _ensure_column(c, "retention_decision", "retention_decision TEXT NOT NULL DEFAULT 'new'")
        _ensure_column(c, "retention_reason", "retention_reason TEXT NOT NULL DEFAULT ''")
        _ensure_column(c, "retention_score", "retention_score INTEGER NOT NULL DEFAULT 0")
        c.execute("UPDATE janus_files SET last_touched_at=created_at WHERE last_touched_at=0")
        c.execute("CREATE INDEX IF NOT EXISTS idx_janus_files_audit ON janus_files(pinned,last_touched_at,last_referenced_at)")
        c.execute(
            """CREATE TABLE IF NOT EXISTS janus_file_audit_log(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT NOT NULL,
                account_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                decision TEXT NOT NULL,
                reason TEXT NOT NULL,
                score INTEGER NOT NULL,
                size_bytes INTEGER NOT NULL,
                store_bytes_before INTEGER NOT NULL,
                created_at INTEGER NOT NULL
            )"""
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_janus_file_audit_created ON janus_file_audit_log(created_at DESC)")


def _effective_touch(row: sqlite3.Row) -> int:
    return max(int(row["created_at"] or 0), int(row["last_touched_at"] or 0), int(row["last_referenced_at"] or 0))


def _store_bytes(c: sqlite3.Connection) -> int:
    row = c.execute("SELECT COALESCE(SUM(size_bytes),0) AS n FROM janus_files").fetchone()
    return int(row["n"] or 0)


def touch_file(file_id: str, account_id: int, *, referenced: bool = False) -> bool:
    init_retention_schema()
    now = int(time.time())
    with _db() as c:
        if not _table_exists(c, "janus_files"):
            return False
        column = "last_referenced_at" if referenced else "last_touched_at"
        cur = c.execute(f"UPDATE janus_files SET {column}=? WHERE id=? AND account_id=?", (now, file_id, int(account_id)))
        return bool(cur.rowcount)


def _assessment(row: sqlite3.Row, now: int, store_bytes: int, duplicate_count: int) -> tuple[str, int, str]:
    if bool(row["pinned"]):
        return "keep", 100, "Pinned by the user; autonomous deletion is disabled."
    age = now - _effective_touch(row)
    if age < STALE_SECONDS:
        return "keep", 90, "Recently touched; not eligible for pruning."

    name = str(row["original_name"] or "")
    ext = Path(name).suffix.lower()
    text = str(row["extracted_text"] or "").strip()
    size = int(row["size_bytes"] or 0)
    score = 45
    reasons: list[str] = []

    if duplicate_count > 1:
        score -= 35; reasons.append("duplicate content exists within this account")
    if TEMP_NAME_RE.search(name):
        score -= 20; reasons.append("temporary/test-like filename")
    if ext == ".log":
        score -= 18; reasons.append("ephemeral log content")
    if text:
        if len(text) >= 4000:
            score += 25; reasons.append("substantial reusable extracted text")
        elif len(text) >= 800:
            score += 14; reasons.append("meaningful extracted text")
        elif len(text) < 160:
            score -= 15; reasons.append("very little reusable text")
    elif ext in {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif"}:
        score += 8; reasons.append("document/image may retain semantic value")

    if size >= 4 * 1024 * 1024:
        score -= 8; reasons.append("large storage cost")
    if store_bytes >= HARD_STORAGE_BYTES:
        score -= 30; reasons.append("storage above hard threshold")
    elif store_bytes >= SOFT_STORAGE_BYTES:
        score -= 18; reasons.append("storage above soft threshold")

    stale_days = age / 86400.0
    if stale_days >= 30:
        score -= 12; reasons.append("untouched at least 30 days")
    elif stale_days >= 14:
        score -= 6; reasons.append("untouched at least 14 days")

    score = max(0, min(100, score))
    threshold = 35 if store_bytes < SOFT_STORAGE_BYTES else 50
    decision = "delete" if score < threshold else "keep"
    if not reasons:
        reasons.append("ordinary stale attachment")
    return decision, score, "; ".join(reasons) + f"; score {score}/{threshold} delete threshold"


def audit_storage(*, force: bool = False, max_files: int = 200) -> dict:
    global _last_result
    init_retention_schema()
    now = int(time.time())
    with _db() as c:
        if not _table_exists(c, "janus_files"):
            _last_result = {"ran": False, "reason": "file table unavailable", "at": now}
            return _last_result
        meta_exists = _table_exists(c, "janus_core_runtime_meta")
        last = 0
        if meta_exists:
            row = c.execute("SELECT value FROM janus_core_runtime_meta WHERE key='file_storage_last_audit'").fetchone()
            if row:
                try: last = int(row["value"] or 0)
                except Exception: last = 0
        if not force and last and now - last < AUDIT_INTERVAL_SECONDS:
            _last_result = {"ran": False, "reason": "audit interval not reached", "last_audit_at": last}
            return _last_result

        store_before = _store_bytes(c)
        rows = c.execute(
            "SELECT * FROM janus_files WHERE pinned=0 AND MAX(created_at,last_touched_at,last_referenced_at)<=? ORDER BY MAX(created_at,last_touched_at,last_referenced_at) ASC LIMIT ?",
            (now - STALE_SECONDS, max(1, int(max_files))),
        ).fetchall()
        duplicate_counts = {
            row["sha256"]: int(c.execute("SELECT COUNT(*) FROM janus_files WHERE sha256=? AND account_id=?", (row["sha256"], int(row["account_id"]))).fetchone()[0])
            for row in rows
        }

        current_bytes = store_before
        kept = deleted = bytes_freed = 0
        decisions: list[dict] = []
        for row in rows:
            decision, score, reason = _assessment(row, now, current_bytes, duplicate_counts.get(row["sha256"], 1))
            c.execute(
                "UPDATE janus_files SET last_audited_at=?,retention_decision=?,retention_reason=?,retention_score=? WHERE id=?",
                (now, decision, reason, score, row["id"]),
            )
            c.execute(
                "INSERT INTO janus_file_audit_log(file_id,account_id,filename,decision,reason,score,size_bytes,store_bytes_before,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (row["id"], int(row["account_id"]), row["original_name"], decision, reason, score, int(row["size_bytes"]), current_bytes, now),
            )
            if decision == "delete":
                try:
                    (FILE_ROOT / row["storage_name"]).unlink(missing_ok=True)
                    c.execute("DELETE FROM janus_files WHERE id=?", (row["id"],))
                    deleted += 1
                    bytes_freed += int(row["size_bytes"])
                    current_bytes = max(0, current_bytes - int(row["size_bytes"]))
                except Exception as exc:
                    decision = "keep"
                    reason = f"Deletion failed safely: {type(exc).__name__}"
                    kept += 1
                    c.execute(
                        "UPDATE janus_files SET retention_decision='keep',retention_reason=? WHERE id=?",
                        (reason, row["id"]),
                    )
            else:
                kept += 1
            decisions.append({"id": row["id"], "filename": row["original_name"], "decision": decision, "score": score, "reason": reason})

        if meta_exists:
            c.execute(
                "INSERT INTO janus_core_runtime_meta(key,value,updated_at) VALUES('file_storage_last_audit',?,datetime('now')) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",
                (str(now),),
            )
        _last_result = {
            "ran": True,
            "audited": len(rows),
            "kept": kept,
            "deleted": deleted,
            "bytes_freed": bytes_freed,
            "store_bytes_before": store_before,
            "store_bytes_after": current_bytes,
            "soft_limit_bytes": SOFT_STORAGE_BYTES,
            "hard_limit_bytes": HARD_STORAGE_BYTES,
            "stale_seconds": STALE_SECONDS,
            "at": now,
            "decisions": decisions[-50:],
        }
        return _last_result


def _publish_to_society(janus_sleep_cycle, result: dict) -> None:
    if not result.get("ran"):
        return
    summary = (
        f"Global storage audit: assessed {result.get('audited',0)} stale files; "
        f"kept {result.get('kept',0)}, deleted {result.get('deleted',0)}, "
        f"freed {result.get('bytes_freed',0)} bytes; store now {result.get('store_bytes_after',0)} bytes."
    )
    try:
        janus_sleep_cycle.send("interface", "evidence", summary, "storage_audit")
        janus_sleep_cycle.send("interface", "memory", summary, "storage_audit")
        janus_sleep_cycle.send("interface", "safety", summary, "storage_audit")
        janus_sleep_cycle.service_work_burst(include_interface=True, only_if_pending=True)
    except Exception:
        pass


def _worker(janus_sleep_cycle) -> None:
    while True:
        try:
            result = audit_storage(force=False)
            _publish_to_society(janus_sleep_cycle, result)
        except Exception:
            pass
        time.sleep(WORKER_POLL_SECONDS)


def install_storage_auditor(app, janus_sleep_cycle) -> None:
    global _worker_started
    init_retention_schema()

    @app.middleware("http")
    async def mark_file_access(request: Request, call_next):
        response = await call_next(request)
        try:
            if response.status_code < 400 and request.method == "GET" and request.url.path.startswith("/files/"):
                parts = request.url.path.strip("/").split("/")
                if len(parts) >= 2 and parts[1] not in {"audit", "storage"}:
                    account = auth.account_for_token(auth._bearer(request.headers.get("authorization")))
                    if account:
                        touch_file(parts[1], int(account["id"]))
        except Exception:
            pass
        return response

    @app.post("/files/{file_id}/pin", tags=["files"])
    def pin_file(file_id: str, req: PinRequest, authorization: Optional[str] = Header(default=None)):
        account = auth.require_account(authorization)
        init_retention_schema()
        now = int(time.time())
        with _db() as c:
            cur = c.execute(
                "UPDATE janus_files SET pinned=?,last_touched_at=?,retention_decision=?,retention_reason=? WHERE id=? AND account_id=?",
                (1 if req.pinned else 0, now, "keep" if req.pinned else "reassess", "Pinned by user" if req.pinned else "Unpinned; eligible for future JANUS audit", file_id, int(account["id"])),
            )
            if not cur.rowcount:
                raise HTTPException(404, "File not found")
        return {"ok": True, "id": file_id, "pinned": req.pinned}

    @app.get("/files/audit/recent", tags=["files"])
    def recent_file_audits(authorization: Optional[str] = Header(default=None)):
        account = auth.require_account(authorization)
        init_retention_schema()
        with _db() as c:
            rows = c.execute("SELECT * FROM janus_file_audit_log WHERE account_id=? ORDER BY id DESC LIMIT 100", (int(account["id"]),)).fetchall()
        return {"ok": True, "items": [dict(r) for r in rows]}

    @app.get("/files/storage/status", tags=["files"])
    def file_storage_status(authorization: Optional[str] = Header(default=None)):
        auth.require_account(authorization)
        init_retention_schema()
        with _db() as c:
            total = _store_bytes(c) if _table_exists(c, "janus_files") else 0
            count = int(c.execute("SELECT COUNT(*) FROM janus_files").fetchone()[0]) if _table_exists(c, "janus_files") else 0
        return {
            "ok": True, "files": count, "bytes": total,
            "soft_limit_bytes": SOFT_STORAGE_BYTES, "hard_limit_bytes": HARD_STORAGE_BYTES,
            "stale_after_seconds": STALE_SECONDS, "audit_interval_seconds": AUDIT_INTERVAL_SECONDS,
            "last_audit": _last_result,
        }

    with _worker_lock:
        if not _worker_started:
            _worker_started = True
            thread = threading.Thread(target=_worker, args=(janus_sleep_cycle,), name="janus-file-storage-auditor", daemon=True)
            thread.start()
