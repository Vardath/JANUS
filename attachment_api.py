"""Authenticated, account-bound file storage for JANUS.

Upload, validation, hashing, storage, listing, download and deletion are ordinary
application operations. Text/code/PDF and common office documents are extracted
locally so document grounding can usually run without a model/API call.
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
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pypdf import PdfReader

import auth
import document_grounding

router = APIRouter(prefix="/files", tags=["files"])
DB_PATH = Path(os.getenv("JANUS_DB_PATH", "/data/janus.sqlite3"))
FILE_ROOT = Path(os.getenv("JANUS_FILE_DIR", "/data/janus_files"))
MAX_FILE_BYTES = max(64 * 1024, int(os.getenv("JANUS_MAX_FILE_BYTES", str(8 * 1024 * 1024))))
MAX_TEXT_CACHE_BYTES = max(16 * 1024, int(os.getenv("JANUS_MAX_TEXT_CACHE_BYTES", str(512 * 1024))))
MAX_PDF_TEXT_CHARS = max(16000, int(os.getenv("JANUS_MAX_PDF_TEXT_CHARS", "250000")))
MAX_PDF_PAGES = max(1, int(os.getenv("JANUS_MAX_PDF_PAGES", "80")))
MAX_OFFICE_TEXT_CHARS = max(32000, int(os.getenv("JANUS_MAX_OFFICE_TEXT_CHARS", "350000")))
MAX_OFFICE_UNCOMPRESSED = max(1024 * 1024, int(os.getenv("JANUS_MAX_OFFICE_UNCOMPRESSED_BYTES", str(12 * 1024 * 1024))))

OFFICE_EXTENSIONS = {".docx", ".pptx", ".xlsx", ".odt"}
ALLOWED_EXTENSIONS = {
    ".txt", ".md", ".markdown", ".json", ".jsonl", ".csv", ".tsv", ".log",
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".kt", ".kts", ".swift",
    ".c", ".h", ".cpp", ".hpp", ".cs", ".go", ".rs", ".rb", ".php", ".sh",
    ".bash", ".zsh", ".ps1", ".bat", ".cmd", ".xml", ".yaml", ".yml", ".toml",
    ".ini", ".cfg", ".conf", ".sql", ".html", ".htm", ".css", ".rtf", ".pdf",
    ".docx", ".pptx", ".xlsx", ".odt",
    ".png", ".jpg", ".jpeg", ".webp", ".gif",
}
TEXT_EXTENSIONS = ALLOWED_EXTENSIONS - {".pdf", ".docx", ".pptx", ".xlsx", ".odt", ".png", ".jpg", ".jpeg", ".webp", ".gif"}


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
    document_grounding.init_schema()


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
                chunks.append(block[:remaining]); truncated = True; break
            chunks.append(block); chars += len(block)
        result = "\n".join(chunks).strip()
        if not result:
            return None, "pdf_no_text"
        return result, "pdf_cached_truncated" if truncated else "pdf_cached"
    except Exception:
        return None, "pdf_failed"


def _safe_zip(data: bytes) -> zipfile.ZipFile:
    z = zipfile.ZipFile(io.BytesIO(data))
    total = sum(max(0, int(i.file_size)) for i in z.infolist())
    if total > MAX_OFFICE_UNCOMPRESSED:
        z.close()
        raise ValueError("office archive expands beyond safe extraction limit")
    return z


def _xml_text(blob: bytes, tags: set[str] | None = None) -> str:
    root = ET.fromstring(blob)
    out: list[str] = []
    for el in root.iter():
        local = el.tag.rsplit("}", 1)[-1]
        if el.text and (tags is None or local in tags):
            t = el.text.strip()
            if t:
                out.append(t)
        if local in {"p", "tr", "row"} and out:
            out.append("\n")
    text = " ".join(out)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def _extract_office_text(ext: str, data: bytes) -> tuple[Optional[str], str]:
    try:
        z = _safe_zip(data)
        names = z.namelist()
        pieces: list[str] = []
        if ext == ".docx":
            targets = [n for n in names if n == "word/document.xml" or n.startswith("word/header") or n.startswith("word/footer")]
            for n in targets:
                text = _xml_text(z.read(n), {"t"})
                if text: pieces.append(text)
        elif ext == ".pptx":
            targets = sorted(n for n in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", n))
            for i, n in enumerate(targets, 1):
                text = _xml_text(z.read(n), {"t"})
                if text: pieces.append(f"[Slide {i}]\n{text}")
        elif ext == ".xlsx":
            shared: list[str] = []
            if "xl/sharedStrings.xml" in names:
                root = ET.fromstring(z.read("xl/sharedStrings.xml"))
                for si in root.iter():
                    if si.tag.rsplit("}",1)[-1] == "si":
                        vals = [x.text or "" for x in si.iter() if x.tag.rsplit("}",1)[-1] == "t"]
                        shared.append("".join(vals))
            sheets = sorted(n for n in names if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n))
            for idx, n in enumerate(sheets, 1):
                root = ET.fromstring(z.read(n)); rows: list[str] = []
                for row in root.iter():
                    if row.tag.rsplit("}",1)[-1] != "row": continue
                    vals: list[str] = []
                    for cell in row:
                        if cell.tag.rsplit("}",1)[-1] != "c": continue
                        typ = cell.attrib.get("t", "")
                        v = next((x.text for x in cell if x.tag.rsplit("}",1)[-1] == "v"), None)
                        if v is None: continue
                        if typ == "s":
                            try: vals.append(shared[int(v)])
                            except Exception: vals.append(v)
                        else: vals.append(v)
                    if vals: rows.append("\t".join(vals))
                if rows: pieces.append(f"[Sheet {idx}]\n" + "\n".join(rows))
        elif ext == ".odt":
            if "content.xml" in names:
                pieces.append(_xml_text(z.read("content.xml"), None))
        z.close()
        result = "\n\n".join(x for x in pieces if x).strip()
        if not result:
            return None, f"{ext[1:]}_no_text"
        truncated = len(result) > MAX_OFFICE_TEXT_CHARS
        if truncated: result = result[:MAX_OFFICE_TEXT_CHARS]
        return result, f"{ext[1:]}_cached_truncated" if truncated else f"{ext[1:]}_cached"
    except Exception:
        return None, f"{ext[1:]}_failed"


def _extract_rtf(data: bytes) -> tuple[Optional[str], str]:
    sample = data[:MAX_TEXT_CACHE_BYTES].decode("latin-1", errors="replace")
    text = re.sub(r"\\'[0-9a-fA-F]{2}", " ", sample)
    text = re.sub(r"\\[a-zA-Z]+-?\d* ?", " ", text)
    text = text.replace("{", " ").replace("}", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return (text or None), "rtf_cached" if text else "rtf_failed"


def _extract_text(filename: str, data: bytes) -> tuple[Optional[str], str]:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return _extract_pdf_text(data)
    if ext in OFFICE_EXTENSIONS:
        return _extract_office_text(ext, data)
    if ext == ".rtf":
        return _extract_rtf(data)
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


def store_generated_file(account_id: int, filename: str, data: bytes, mime_type: str = "text/markdown") -> dict:
    """Store server-generated bytes through the same account-bound file subsystem.

    This is intentionally not an unauthenticated route. Callers must already have
    resolved an authenticated account and pass its numeric id. Generated text is
    indexed exactly like an uploaded document so later JANUS grounding can retrieve it.
    """
    _init_db()
    filename = _clean_filename(filename)
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported generated file type: {ext or 'no extension'}")
    if not data or len(data) > MAX_FILE_BYTES:
        raise ValueError("Generated file is empty or exceeds the configured file limit")
    digest = hashlib.sha256(data).hexdigest()
    mime = (mime_type or "application/octet-stream").strip().lower()[:120]
    now = int(time.time()); file_id = uuid.uuid4().hex
    storage_name = f"{int(account_id)}-{file_id}{ext}"; target = FILE_ROOT / storage_name; tmp = FILE_ROOT / f".{storage_name}.tmp"
    extracted, extraction_status = _extract_text(filename, data)
    try:
        with open(tmp, "wb") as f:
            f.write(data); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, target)
        with _db() as c:
            c.execute(
                """INSERT INTO janus_files(id,account_id,original_name,mime_type,size_bytes,sha256,storage_name,extracted_text,extraction_status,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (file_id, int(account_id), filename, mime, len(data), digest, storage_name, extracted, extraction_status, now),
            )
        if extracted:
            document_grounding.index_text(int(account_id), file_id, extracted, force=True)
    except Exception:
        tmp.unlink(missing_ok=True); target.unlink(missing_ok=True); document_grounding.delete_index(file_id, int(account_id)); raise
    with _db() as c:
        row = c.execute("SELECT * FROM janus_files WHERE id=? AND account_id=?", (file_id, int(account_id))).fetchone()
    meta = _metadata(row)
    if extracted:
        meta["document_index"] = document_grounding.ensure_file_index(int(account_id), file_id)
    return meta


def cleanup_account_files(account_id: int) -> int:
    _init_db(); removed = 0
    with _db() as c:
        rows = c.execute("SELECT id,storage_name FROM janus_files WHERE account_id=?", (int(account_id),)).fetchall()
        for row in rows:
            try:
                (FILE_ROOT / row["storage_name"]).unlink(missing_ok=True); removed += 1
            except Exception:
                pass
            document_grounding.delete_index(str(row["id"]), int(account_id))
        c.execute("DELETE FROM janus_files WHERE account_id=?", (int(account_id),))
    return removed


@router.post("/upload")
def upload_file(req: UploadRequest, authorization: Optional[str] = Header(default=None)):
    account = _require_account(authorization); _init_db()
    filename = _clean_filename(req.filename); ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(415, f"Unsupported file type: {ext or 'no extension'}")
    data = _decode_upload(req.data_base64); digest = hashlib.sha256(data).hexdigest()
    mime = (req.mime_type or "application/octet-stream").strip().lower()[:120]
    now = int(time.time()); file_id = uuid.uuid4().hex
    storage_name = f"{int(account['id'])}-{file_id}{ext}"; target = FILE_ROOT / storage_name; tmp = FILE_ROOT / f".{storage_name}.tmp"
    extracted, extraction_status = _extract_text(filename, data)
    try:
        with open(tmp, "wb") as f:
            f.write(data); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, target)
        with _db() as c:
            c.execute(
                """INSERT INTO janus_files(id,account_id,original_name,mime_type,size_bytes,sha256,storage_name,extracted_text,extraction_status,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (file_id, int(account["id"]), filename, mime, len(data), digest, storage_name, extracted, extraction_status, now),
            )
        if extracted:
            document_grounding.index_text(int(account["id"]), file_id, extracted, force=True)
    except Exception:
        tmp.unlink(missing_ok=True); target.unlink(missing_ok=True); document_grounding.delete_index(file_id, int(account["id"])); raise
    with _db() as c:
        row = c.execute("SELECT * FROM janus_files WHERE id=?", (file_id,)).fetchone()
    meta = _metadata(row)
    if extracted:
        meta["document_index"] = document_grounding.ensure_file_index(int(account["id"]), file_id)
    return {"ok": True, "file": meta}


@router.get("")
def list_files(authorization: Optional[str] = Header(default=None)):
    account = _require_account(authorization); _init_db()
    with _db() as c:
        rows = c.execute("SELECT * FROM janus_files WHERE account_id=? ORDER BY created_at DESC LIMIT 250", (int(account["id"]),)).fetchall()
    return {"ok": True, "items": [_metadata(row) for row in rows]}


@router.get("/{file_id}")
def file_info(file_id: str, authorization: Optional[str] = Header(default=None)):
    account = _require_account(authorization); _init_db()
    with _db() as c:
        row = c.execute("SELECT * FROM janus_files WHERE id=? AND account_id=?", (file_id, int(account["id"]))).fetchone()
    if not row: raise HTTPException(404, "File not found")
    meta = _metadata(row)
    if row["extracted_text"]:
        meta["document_index"] = document_grounding.ensure_file_index(int(account["id"]), file_id)
    return {"ok": True, "file": meta}


@router.get("/{file_id}/download")
def download_file(file_id: str, authorization: Optional[str] = Header(default=None)):
    account = _require_account(authorization); _init_db()
    with _db() as c:
        row = c.execute("SELECT * FROM janus_files WHERE id=? AND account_id=?", (file_id, int(account["id"]))).fetchone()
    if not row: raise HTTPException(404, "File not found")
    path = FILE_ROOT / row["storage_name"]
    if not path.is_file(): raise HTTPException(410, "File metadata exists but stored bytes are unavailable")
    return FileResponse(path, media_type=row["mime_type"], filename=row["original_name"])


@router.delete("/{file_id}")
def delete_file(file_id: str, authorization: Optional[str] = Header(default=None)):
    account = _require_account(authorization); _init_db()
    with _db() as c:
        row = c.execute("SELECT * FROM janus_files WHERE id=? AND account_id=?", (file_id, int(account["id"]))).fetchone()
        if not row: raise HTTPException(404, "File not found")
        try:
            (FILE_ROOT / row["storage_name"]).unlink(missing_ok=True)
        except Exception as exc:
            raise HTTPException(500, f"Unable to delete stored file: {type(exc).__name__}")
        document_grounding.delete_index(file_id, int(account["id"]))
        c.execute("DELETE FROM janus_files WHERE id=? AND account_id=?", (file_id, int(account["id"])))
    return {"ok": True, "deleted": True, "id": file_id}


_init_db()