from __future__ import annotations

import base64
import os
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException

from . import auth, governance, sensory_bus, storage

router = APIRouter()


def _generate(account_id: int, prompt: str, *, automatic: bool = False) -> dict[str, Any]:
    scope = "automatic_explanatory_image" if automatic else "image"
    if not governance.permit(account_id, scope, 0.04):
        raise HTTPException(429, "JANUS image generation budget reached for this account")
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
        result = client.images.generate(
            model=os.getenv("JANUS_IMAGE_MODEL", "gpt-image-1"),
            prompt=prompt[:4000],
            size="1024x1024",
            quality=os.getenv("JANUS_IMAGE_QUALITY", "medium"),
        )
        raw = base64.b64decode(result.data[0].b64_json)
    except Exception as exc:
        raise HTTPException(502, f"Image generation failed: {type(exc).__name__}")
    file = storage.save_file(account_id, "janus-generated.png", "image/png", raw)
    storage.add_event(account_id,"interface","automatic_visual" if automatic else "image_generated",f"Generated image {file['id']}",f"Generated image {file['id']}","foreground")
    sensory_bus.ingest(
        account_id,
        "image",
        "generated_visual",
        f"JANUS generated an image artifact for this prompt: {prompt[:2200]}",
        salience=0.7 if automatic else 0.82,
        uncertainty=0.35,
        novelty=0.72,
        metadata={"file_id": file["id"], "automatic": automatic, "mime_type": "image/png"},
        mode="foreground",
    )
    return {**file,"inline_path":f"/images/{file['id']}/inline","automatic":automatic,"quality":os.getenv("JANUS_IMAGE_QUALITY","medium")}


@router.post("/images/generate")
def generate(payload: dict[str, Any], authorization: Optional[str] = Header(default=None)):
    account = auth.require_account(authorization)
    prompt = str(payload.get("prompt") or payload.get("description") or "").strip()
    if not prompt: raise HTTPException(400,"prompt required")
    image = _generate(int(account["id"]),prompt,automatic=False)
    return {"ok":True,"generated_image":image,"image":image}


@router.get("/images/usage")
def usage(authorization: Optional[str] = Header(default=None)):
    account=auth.require_account(authorization); aid=int(account["id"])
    count=storage.one("SELECT count(*) n FROM v2_files WHERE account_id=? AND filename='janus-generated.png' AND created_at>?",(aid,storage.now()-86400))
    return {
        "ok":True,"generated_today":int(count["n"] if count else 0),
        "quality":os.getenv("JANUS_IMAGE_QUALITY","medium"),
        "background_multi_core_image_generation":False,
        "automatic_explanatory_images":"rare-and-foreground-only",
    }


def maybe_explanatory_image(account_id: int, message: str, reply: str) -> dict[str, Any] | None:
    """Rare foreground-only visual aid, never a background core image loop."""
    if os.getenv("JANUS_AUTO_EXPLANATORY_IMAGES","1") != "1": return None
    text=(message or "").lower()
    explicit=any(x in text for x in ("show me a diagram","draw a diagram","visualize this","picture would help","image would help"))
    structural=any(x in text for x in ("architecture","flow diagram","topology","how does it connect","visual explanation"))
    if not (explicit or structural): return None
    # Separate, deliberately tiny daily cap for unsolicited/automatic visuals.
    start=storage.now()-86400
    used=storage.one("SELECT coalesce(sum(calls),0) n FROM v2_cost_ledger WHERE account_id=? AND scope='automatic_explanatory_image' AND allowed=1 AND created_at>?",(int(account_id),start))
    if int(used["n"] if used else 0) >= int(os.getenv("JANUS_AUTO_IMAGE_DAILY_CAP","2")): return None
    prompt="Create a clear explanatory diagram for this JANUS answer. Prioritize labels and conceptual clarity over decoration.\nUser request: "+message[:1500]+"\nAnswer context: "+reply[:2000]
    try: return _generate(account_id,prompt,automatic=True)
    except HTTPException: return None
