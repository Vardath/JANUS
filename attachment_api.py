"""Authenticated, account-bound file storage for JANUS.

Upload, validation, hashing, storage, listing, download and deletion are ordinary
application operations. Text/code files and text-bearing PDFs are extracted
locally so most document grounding has no model/API cost.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import io
import os
import re
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pypdf import PdfReader

import auth

router = APIRouter(prefix="/files", tags=["files"])
DB_PATH = Path(os.getenv("JANUS_DB_PATH", "/data/janus.sqlite3"))
FILE_ROOT = Path(os.getenv("JANUS_FILE_DIR", "/data/janus_files"))
MAX_FILE_BYTES = max(64 * 1024, int(os.getenv("JANUS_MAX_FILE_BYTES", str(8 * 1024 * 1024))))
MAX_TEXT_CACHE_BYTES = max(16 * 1024, int(os.getenv("JANUS_MAX_TEXT_CACHE_BYTES", str(512 * 1024))))
MAX_PDF_TEXT_CHARS = max(16000, int(os.getenv("JANUS_MAX_PDF_TEXT_CHARS", "250000")))
MAX_PDF_PAGES = max(1, int(os.getenv("JANUS_MAX_PDF_PAGES", "80")))

ALLOWED_EXTENSIONS = {
    ".txt", ".md", ".markdown", ".json", ".jsonl", ".csv", ".tsv", ".log",
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".kt", ".kts", ".swift",
    ".c", ".h", ".cpp", ".hpp", ".cs", ".go", ".rs", ".rb", ".php", ".sh",
    ".bash", ".zsh", ".ps1", ".bat", ".cmd", ".xml", ".yaml", ".yml", ".toml",
    ".ini", ".cfg", ".conf", ".sql", ".html", ".htm", ".css", ".pdf",
    ".png", ".jpg", ".jpeg", ".webp", ".gif",
}
TEXT_EXTENSIONS = ALLOWED_EXTENSIONS - {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif"}


class UploadRequest(BaseModel):
    filename: str
    mime_type: str = "application/octet-stream"
    data_base64: str


def _db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    return c


def _init_db():
    FILE_ROOT.mkdir(parents=True, exist_ok=True)
    with _db() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS janus_files(
                id TEXT PRIMARY KEY,
                account_id INTEGER NOT NULL,
                original_name TEXT NOT NULL,
                mime_type TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                storage_name TEXT NOT NULL UNIQUE,
                extracted_text TEXT,
                extraction_status TEXT NOT NULL DEFAULT 'not_applicable',
                created_at INTEGER NOT NULL,
                FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE
            )"""
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_janus_files_account_created ON janus_files(account_id,created_at DESC)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_janus_files_hash ON janus_files(account_id,sha256)")


def _require_account(authorization: Optional[str]):
    return auth.require_account(authorization)


def _clean_filename(value: str) -> str:
    name = Path((value or "").replace("\\", "/")).name.strip()
    name = re.sub(r"[\x00-\x1f\x7f]+", "", name)
    if not name or name in {".", ".."}:
        raise HTTPException(400, "A valid filename is required")
    return name[:180]


def _metadata(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "filename": row["original_name"],
        "mime_type": row["mime_type"],
        "size_bytes": int(row["size_bytes"]),
        "sha256": row["sha256"],
        "extraction_status": row["extraction_status"],
        "has_extracted_text": bool(row["extracted_text"]),
        "created_at": int(row["created_at"]),
        "download_path": f"/files/{row['id']}/download",
    }


def _decode_upload(encoded: str) -> bytes:
    raw = (encoded or "").strip()
    if raw.startswith("data:") and "," in raw:
        raw = raw.split(",", 1)[1]
    if len(raw) > ((MAX_FILE_BYTES + 2) // 3) * 4 + 16:
        raise HTTPException(413, f"File exceeds the {MAX_FILE_BYTES} byte upload limit")
    try:
        data = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(400, "File payload is not valid base64")
    if not data:
        raise HTTPException(400, "Empty files are not supported")
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(413, f"File exceeds the {MAX_FILE_BYTES} byte upload limit")
    return data


def _extract_pdf_text(data: bytes) -> tuple[Optional[str], str]:
    try:
        reader = PdfReader(io.BytesIO(data))
        chunks: list[str] = []
        chars = 0
        truncated = False
        for idx, page in enumerate(reader.pages):
            if idx >= MAX_PDF_PAGES:
                truncated = True
                break
            try:
                text = (page.extract_text() or "").strip()
            except Exception:
                text = ""
            if not text:
                continue
            block = f"[PDF page {idx + 1}]\n{text}\n"
            remaining = MAX_PDF_TEXT_CHARS - chars
            if remaining <= 0:
                truncated = True
                break
            if len(block) > remaining:
                chunks.append(block[:remaining])
                chars += remaining
                truncated = True
                break
            chunks.append(block)
            chars += len(block)
        result = "\n".join(chunks).strip()
        if not result:
            return None, "pdf_no_text"
        return result, "pdf_cached_truncated" if truncated else "pdf_cached"
    except Exception:
        return None, "pdf_failed"


def _extract_text(filename: str, data: bytes) -> tuple[Optional[str], str]:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return _extract_pdf_text(data)
    if ext not in TEXT_EXTENSIONS:
        return None, "not_applicable"
    sample = data[:MAX_TEXT_CACHE_BYTES]
    try:
        text = sample.decode("utf-8")
    except UnicodeDecodeError:
        text = sample.decode("utf-8", errors="replace")
    if "\x00" in text[:4096]:
        return None, "failed"
    return text, "cached" if len(data) <= MAX_TEXT_CACHE_BYTES else "cached_truncated"


def cleanup_account_files(account_id: int) -> int:
    _init_db()
    removed = 0
    with _db() as c:
        rows = c.execute("SELECT storage_name FROM janus_files WHERE account_id=?", (int(account_id),)).fetchall()
        for row in rows:
            try:
                (FILE_ROOT / row["storage_name"]).unlink(missing_ok=True)
                removed += 1
            except Exception:
                pass
        c.execute("DELETE FROM janus_files WHERE account_id=?", (int(account_id),))
    return removed


@router.post("/upload")
def upload_file(req: UploadRequest, authorization: Optional[str] = Header(default=None)):
    account = _require_account(authorization)
    _init_db()
    filename = _clean_filename(req.filename)
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(415, f"Unsupported file type: {ext or 'no extension'}")
    data = _decode_upload(req.data_base64)
    digest = hashlib.sha256(data).hexdigest()
    mime = (req.mime_type or "application/octet-stream").strip().lower()[:120]
    now = int(time.time())
    file_id = uuid.uuid4().hex
    storage_name = f"{int(account['id'])}-{file_id}{ext}"
    target = FILE_ROOT / storage_name
    tmp = FILE_ROOT / f".{storage_name}.tmp"
    extracted, extraction_status = _extract_text(filename, data)

    try:
        with open(tmp, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, target)
        with _db() as c:
            c.execute(
                """INSERT INTO janus_files(
                    id,account_id,original_name,mime_type,size_bytes,sha256,storage_name,
                    extracted_text,extraction_status,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (file_id, int(account["id"]), filename, mime, len(data), digest, storage_name,
                 extracted, extraction_status, now),
            )
    except Exception:
        tmp.unlink(missing_ok=True)
        target.unlink(missing_ok=True)
        raise

    with _db() as c:
        row = c.execute("SELECT * FROM janus_files WHERE id=?", (file_id,)).fetchone()
    return {"ok": True, "file": _metadata(row)}


@router.get("")
def list_files(authorization: Optional[str] = Header(default=None)):
    account = _require_account(authorization)
    _init_db()
    with _db() as c:
        rows = c.execute(
            "SELECT * FROM janus_files WHERE account_id=? ORDER BY created_at DESC LIMIT 250",
            (int(account["id"]),),
        ).fetchall()
    return {"ok": True, "items": [_metadata(row) for row in rows]}


@router.get("/{file_id}")
def file_info(file_id: str, authorization: Optional[str] = Header(default=None)):
    account = _require_account(authorization)
    _init_db()
    with _db() as c:
        row = c.execute("SELECT * FROM janus_files WHERE id=? AND account_id=?", (file_id, int(account["id"]))).fetchone()
    if not row:
        raise HTTPException(404, "File not found")
    return {"ok": True, "file": _metadata(row)}


@router.get("/{file_id}/download")
def download_file(file_id: str, authorization: Optional[str] = Header(default=None)):
    account = _require_account(authorization)
    _init_db()
    with _db() as c:
        row = c.execute("SELECT * FROM janus_files WHERE id=? AND account_id=?", (file_id, int(account["id"]))).fetchone()
    if not row:
        raise HTTPException(404, "File not found")
    path = FILE_ROOT / row["storage_name"]
    if not path.is_file():
        raise HTTPException(410, "File metadata exists but stored bytes are unavailable")
    return FileResponse(path, media_type=row["mime_type"], filename=row["original_name"])


@router.delete("/{file_id}")
def delete_file(file_id: str, authorization: Optional[str] = Header(default=None)):
    account = _require_account(authorization)
    _init_db()
    with _db() as c:
        row = c.execute("SELECT * FROM janus_files WHERE id=? AND account_id=?", (file_id, int(account["id"]))).fetchone()
        if not row:
            raise HTTPException(404, "File not found")
        try:
            (FILE_ROOT / row["storage_name"]).unlink(missing_ok=True)
        except Exception as exc:
            raise HTTPException(500, f"Unable to delete stored file: {type(exc).__name__}")
        c.execute("DELETE FROM janus_files WHERE id=? AND account_id=?", (file_id, int(account["id"])))
    return {"ok": True, "deleted": True, "id": file_id}


_init_db()
