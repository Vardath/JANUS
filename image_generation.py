"""Low-cost, bounded JANUS image generation.

Stage 1 only: explicit user-requested images plus rare JANUS-nominated explanatory
images. Multi-core autonomous visual deliberation/render loops remain disabled.
Generated images are stored in the existing account-bound attachment store.
"""
from __future__ import annotations

import base64
import hashlib
import os
import re
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request
from openai import AsyncOpenAI
from pydantic import BaseModel

import auth
import attachment_api

router = APIRouter(prefix="/images", tags=["images"])
DB_PATH = Path(os.getenv("JANUS_DB_PATH", "/data/janus.sqlite3"))
MODEL = os.getenv("JANUS_IMAGE_MODEL", "gpt-image-1-mini")
EXPLICIT_DAILY_CAP = max(1, int(os.getenv("JANUS_IMAGE_EXPLICIT_DAILY_CAP", "6")))
AUTO_DAILY_CAP = max(0, int(os.getenv("JANUS_IMAGE_AUTO_DAILY_CAP", "1")))
GLOBAL_DAILY_CAP = max(1, int(os.getenv("JANUS_IMAGE_GLOBAL_DAILY_CAP", "100")))
AUTO_GLOBAL_DAILY_CAP = max(0, int(os.getenv("JANUS_IMAGE_AUTO_GLOBAL_DAILY_CAP", "20")))
AUTO_COOLDOWN_SECONDS = max(3600, int(os.getenv("JANUS_IMAGE_AUTO_COOLDOWN_SECONDS", str(18 * 3600))))
MAX_PROMPT_CHARS = max(256, int(os.getenv("JANUS_IMAGE_MAX_PROMPT_CHARS", "3000")))
VISUAL_MARKER_RE = re.compile(r"\[\[JANUS_VISUAL:\s*(.*?)\]\]", re.I | re.S)
EXPLICIT_RE = re.compile(r"\b(generate|create|make|draw|render|show me|give me)\b.{0,40}\b(image|picture|illustration|diagram|artwork|visual)\b|\b(image|picture|illustration|diagram|artwork|visual)\b.{0,40}\b(generate|create|make|draw|render)\b", re.I | re.S)
VISUAL_POLICY = """

OPTIONAL VISUAL POLICY:
If the user explicitly asks for an image, picture, illustration, diagram, artwork or visual, you may nominate one render by adding exactly one final marker of the form [[JANUS_VISUAL: concise standalone image prompt]].
You may also nominate a visual without an explicit request only when a picture would materially improve a difficult explanation (for example spatial geometry, architecture, topology, layout, flow, or a visual comparison). Do this rarely, not decoratively.
Do not mention the marker to the user. Do not nominate multiple images. Do not use visual generation for routine chat, emotional emphasis, telemetry, or background self-reflection.
The renderer has separate hard cost/cooldown limits and may decline the nomination.
"""


class GenerateImageRequest(BaseModel):
    prompt: str
    size: str = "1024x1024"
    quality: str = "medium"


def _db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    return c


def _init_db() -> None:
    attachment_api._init_db()
    with _db() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS janus_generated_images(
                id TEXT PRIMARY KEY,
                account_id INTEGER NOT NULL,
                file_id TEXT NOT NULL,
                prompt_hash TEXT NOT NULL,
                prompt TEXT NOT NULL,
                model TEXT NOT NULL,
                quality TEXT NOT NULL,
                size TEXT NOT NULL,
                origin TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE,
                FOREIGN KEY(file_id) REFERENCES janus_files(id) ON DELETE CASCADE
            )"""
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_generated_images_account_time ON janus_generated_images(account_id,created_at DESC)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_generated_images_prompt ON janus_generated_images(account_id,prompt_hash,quality,size)")


def _day_start(now: int) -> int:
    return now - (now % 86400)


def _account_by_profile(profile: str):
    with auth._db() as c:
        return c.execute("SELECT * FROM accounts WHERE username=? COLLATE NOCASE AND disabled=0", (profile,)).fetchone()


def explicit_image_request(message: str) -> bool:
    return bool(EXPLICIT_RE.search(message or ""))


def extract_visual_nomination(reply: str) -> tuple[str, Optional[str]]:
    text = reply or ""
    m = VISUAL_MARKER_RE.search(text)
    if not m:
        return text, None
    prompt = re.sub(r"\s+", " ", m.group(1)).strip()[:MAX_PROMPT_CHARS]
    clean = VISUAL_MARKER_RE.sub("", text).strip()
    return clean, prompt or None


def _budget_check(account_id: int, origin: str, now: int) -> tuple[bool, str]:
    start = _day_start(now)
    with _db() as c:
        user_count = int(c.execute("SELECT COUNT(*) FROM janus_generated_images WHERE account_id=? AND created_at>=?", (account_id, start)).fetchone()[0])
        global_count = int(c.execute("SELECT COUNT(*) FROM janus_generated_images WHERE created_at>=?", (start,)).fetchone()[0])
        if global_count >= GLOBAL_DAILY_CAP:
            return False, "global daily image budget reached"
        if origin == "auto":
            auto_user = int(c.execute("SELECT COUNT(*) FROM janus_generated_images WHERE account_id=? AND origin='auto' AND created_at>=?", (account_id, start)).fetchone()[0])
            auto_global = int(c.execute("SELECT COUNT(*) FROM janus_generated_images WHERE origin='auto' AND created_at>=?", (start,)).fetchone()[0])
            last = c.execute("SELECT created_at FROM janus_generated_images WHERE account_id=? AND origin='auto' ORDER BY created_at DESC LIMIT 1", (account_id,)).fetchone()
            if AUTO_DAILY_CAP <= 0 or auto_user >= AUTO_DAILY_CAP:
                return False, "account automatic-image budget reached"
            if AUTO_GLOBAL_DAILY_CAP <= 0 or auto_global >= AUTO_GLOBAL_DAILY_CAP:
                return False, "global automatic-image budget reached"
            if last and now - int(last["created_at"] or 0) < AUTO_COOLDOWN_SECONDS:
                return False, "automatic-image cooldown active"
        elif user_count >= EXPLICIT_DAILY_CAP:
            return False, "account daily image budget reached"
    return True, "ok"


def _cached(account_id: int, prompt_hash: str, quality: str, size: str):
    with _db() as c:
        return c.execute(
            """SELECT g.*,f.original_name,f.mime_type,f.size_bytes,f.sha256,f.created_at AS file_created_at
               FROM janus_generated_images g JOIN janus_files f ON f.id=g.file_id
               WHERE g.account_id=? AND g.prompt_hash=? AND g.quality=? AND g.size=?
               ORDER BY g.created_at DESC LIMIT 1""",
            (account_id, prompt_hash, quality, size),
        ).fetchone()


def _store_image(account_id: int, prompt: str, quality: str, size: str, origin: str, data: bytes) -> dict:
    attachment_api._init_db()
    now = int(time.time())
    file_id = uuid.uuid4().hex
    digest = hashlib.sha256(data).hexdigest()
    storage_name = f"{account_id}-{file_id}.png"
    target = attachment_api.FILE_ROOT / storage_name
    tmp = attachment_api.FILE_ROOT / f".{storage_name}.tmp"
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, target)
    with attachment_api._db() as c:
        c.execute(
            """INSERT INTO janus_files(id,account_id,original_name,mime_type,size_bytes,sha256,storage_name,extracted_text,extraction_status,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (file_id, account_id, f"janus-image-{now}.png", "image/png", len(data), digest, storage_name, None, "not_applicable", now),
        )
    image_id = uuid.uuid4().hex
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    with _db() as c:
        c.execute(
            "INSERT INTO janus_generated_images(id,account_id,file_id,prompt_hash,prompt,model,quality,size,origin,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (image_id, account_id, file_id, prompt_hash, prompt, MODEL, quality, size, origin, now),
        )
    return {"id": image_id, "file_id": file_id, "mime_type": "image/png", "size_bytes": len(data), "quality": quality, "size": size, "origin": origin, "model": MODEL, "download_path": f"/files/{file_id}/download"}


async def generate_for_account(account, prompt: str, *, origin: str, quality: Optional[str] = None, size: str = "1024x1024") -> dict:
    _init_db()
    prompt = re.sub(r"\s+", " ", (prompt or "")).strip()[:MAX_PROMPT_CHARS]
    if len(prompt) < 3:
        return {"generated": False, "reason": "image prompt is empty"}
    if size not in {"1024x1024", "1024x1536", "1536x1024"}:
        size = "1024x1024"
    quality = quality or "medium"
    if quality not in {"low", "medium"}:
        quality = "medium"
    account_id = int(account["id"])
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    cached = _cached(account_id, prompt_hash, quality, size)
    if cached:
        return {"generated": True, "cached": True, "image": {"id": cached["id"], "file_id": cached["file_id"], "mime_type": cached["mime_type"], "size_bytes": int(cached["size_bytes"]), "quality": cached["quality"], "size": cached["size"], "origin": cached["origin"], "model": cached["model"], "download_path": f"/files/{cached['file_id']}/download"}}
    ok, reason = _budget_check(account_id, origin, int(time.time()))
    if not ok:
        return {"generated": False, "reason": reason}
    if not os.getenv("OPENAI_API_KEY"):
        return {"generated": False, "reason": "image model unavailable"}
    response = await AsyncOpenAI().images.generate(model=MODEL, prompt=prompt, size=size, quality=quality)
    if not response.data:
        return {"generated": False, "reason": "image model returned no image"}
    b64 = getattr(response.data[0], "b64_json", None)
    if not b64:
        return {"generated": False, "reason": "image model returned no embedded image bytes"}
    try:
        data = base64.b64decode(b64)
    except Exception:
        return {"generated": False, "reason": "image result could not be decoded"}
    image = _store_image(account_id, prompt, quality, size, origin, data)
    return {"generated": True, "cached": False, "image": image}


async def maybe_generate_for_chat(profile: str, message: str, reply: str) -> tuple[str, Optional[dict]]:
    account = _account_by_profile(profile)
    if not account:
        return reply, None
    clean_reply, nominated = extract_visual_nomination(reply)
    explicit = explicit_image_request(message)
    if explicit:
        prompt = nominated or message
        result = await generate_for_account(account, prompt, origin="explicit", quality="medium")
        return clean_reply, result
    if nominated:
        result = await generate_for_account(account, nominated, origin="auto", quality="medium")
        return clean_reply, result
    return clean_reply, None


def install_chat_image_bridge(app, interface_chat_module) -> None:
    """Wrap the already secured desktop chat route with bounded image rendering."""
    if getattr(app.state, "janus_image_chat_bridge", False):
        return
    route = next((r for r in app.router.routes if getattr(r, "path", None) == "/desktop/chat" and "POST" in getattr(r, "methods", set())), None)
    if route is None:
        raise RuntimeError("secure /desktop/chat route missing before image bridge install")
    chat_impl = route.endpoint
    app.router.routes[:] = [r for r in app.router.routes if not (getattr(r, "path", None) == "/desktop/chat" and "POST" in getattr(r, "methods", set()))]
    if VISUAL_POLICY not in str(getattr(interface_chat_module, "JANUS_SELF_KNOWLEDGE", "")):
        interface_chat_module.JANUS_SELF_KNOWLEDGE = str(getattr(interface_chat_module, "JANUS_SELF_KNOWLEDGE", "")) + VISUAL_POLICY

    @app.post("/desktop/chat", tags=["desktop"])
    async def chat_with_optional_image(request: Request, payload: dict):
        result = await chat_impl(request=request, payload=payload)
        if not isinstance(result, dict) or not str(result.get("reply") or "").strip():
            return result
        profile = str(result.get("profile") or "").strip()
        if not profile:
            return result
        message = str(payload.get("message") or payload.get("text") or "")
        reply = str(result.get("reply") or "")
        clean_reply, image_result = await maybe_generate_for_chat(profile, message, reply)
        result["reply"] = clean_reply
        if image_result is not None:
            result["image_generation"] = image_result
            if image_result.get("generated"):
                result["image"] = image_result.get("image")
        return result

    app.state.janus_image_chat_bridge = True


@router.post("/generate")
async def generate_image(req: GenerateImageRequest, authorization: Optional[str] = Header(default=None)):
    account = auth.require_account(authorization)
    result = await generate_for_account(account, req.prompt, origin="explicit", quality=req.quality, size=req.size)
    if not result.get("generated"):
        raise HTTPException(429 if "budget" in str(result.get("reason")) or "cooldown" in str(result.get("reason")) else 503, str(result.get("reason") or "image generation unavailable"))
    return {"ok": True, **result}


@router.get("/usage")
def image_usage(authorization: Optional[str] = Header(default=None)):
    account = auth.require_account(authorization)
    _init_db()
    now = int(time.time()); start = _day_start(now)
    with _db() as c:
        total = int(c.execute("SELECT COUNT(*) FROM janus_generated_images WHERE account_id=? AND created_at>=?", (int(account["id"]), start)).fetchone()[0])
        auto = int(c.execute("SELECT COUNT(*) FROM janus_generated_images WHERE account_id=? AND origin='auto' AND created_at>=?", (int(account["id"]), start)).fetchone()[0])
    return {"ok": True, "today": total, "automatic_today": auto, "explicit_daily_cap": EXPLICIT_DAILY_CAP, "automatic_daily_cap": AUTO_DAILY_CAP, "automatic_cooldown_seconds": AUTO_COOLDOWN_SECONDS, "global_daily_cap": GLOBAL_DAILY_CAP, "automatic_global_daily_cap": AUTO_GLOBAL_DAILY_CAP, "model": MODEL, "multi_core_background_rendering": False}


_init_db()
