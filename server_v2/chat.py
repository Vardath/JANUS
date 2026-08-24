from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException

from . import auth, governance, images, media, storage, visual_memory
from .mind import mind

router = APIRouter()


def _visual_assessment(account_id: int, row, prompt: str) -> str:
    cached = visual_memory.get(account_id, str(row["id"]))
    if cached:
        return str(cached["assessment"])
    if not str(row["mime_type"]).startswith("image/"):
        return ""
    if not governance.permit(account_id, "vision", 0.002):
        return ""
    try:
        from openai import OpenAI
        data = Path(row["storage_path"]).read_bytes()
        encoded = base64.b64encode(data).decode("ascii")
        model = os.getenv("JANUS_MODEL", "gpt-5.6")
        result = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "")).responses.create(
            model=model,
            input=[{"role":"user","content":[
                {"type":"input_text","text":"Create a factual externalizable visual assessment for the JANUS Evidence/Context specialist layer. User request: " + prompt[:2000]},
                {"type":"input_image","image_url":f"data:{row['mime_type']};base64,{encoded}"},
            ]}],
        )
        text = (getattr(result, "output_text", "") or "").strip()[:16000]
        if text:
            visual_memory.store(account_id, str(row["id"]), text, model)
            storage.add_event(account_id,"evidence","visual_assessment",f"Visual assessment stored for {row['filename']}",f"Visual assessment stored for {row['filename']}","foreground")
        return text
    except Exception:
        return ""


def _evidence(account_id: int, ids: list[str], message: str) -> tuple[str,list[dict[str,Any]]]:
    blocks=[]; files=[]
    for fid in ids[:4]:
        row=storage.get_file(account_id,fid)
        if not row: raise HTTPException(404,"Attached file not found")
        meta={"id":row["id"],"filename":row["filename"],"mime_type":row["mime_type"],"size_bytes":row["size_bytes"]}
        text=str(row["extracted_text"] or "").strip()
        if text:
            blocks.append(f"SOURCE DOCUMENT {row['filename']}:\n{text[:12000]}")
            meta["grounded"]=True
        assessment=_visual_assessment(account_id,row,message)
        if assessment:
            blocks.append(f"SOURCE IMAGE {row['filename']} — PERSISTED VISUAL ASSESSMENT:\n{assessment[:12000]}")
            meta["visual_analysis"]=True
        files.append(meta)
    lower=message.lower()
    if not ids and any(x in lower for x in ("image i sent","photo i sent","picture i sent","screenshot i sent","previous image","earlier image","that image","that photo")):
        prior=visual_memory.retrieve(account_id,message,5)
        for x in prior:
            blocks.append(f"RECALLED VISUAL MEMORY {x['filename']}:\n{str(x['assessment'])[:6000]}")
    return "\n\n---\n\n".join(blocks)[:26000],files


def _youtube_research(account_id: int, message: str) -> tuple[str,list[dict[str,str]]]:
    transcript=media.youtube_transcript(message)
    if transcript["matched"] and transcript["text"]:
        source=[transcript["source"]] if transcript["source"] else []
        text="YouTube transcript retrieved:\n"+transcript["text"]
        storage.execute("INSERT INTO v2_research(account_id,mode,query,result,sources_json,useful,created_at) VALUES(?,?,?,?,?,?,?)",(account_id,"foreground_youtube",message,text,storage.jdump(source),None,storage.now()))
        return text,source
    return "",[]


@router.post("/desktop/chat")
def chat(payload: dict[str,Any], authorization: Optional[str]=Header(default=None)):
    account=auth.require_account(authorization); aid=int(account["id"])
    message=str(payload.get("message") or payload.get("text") or "").strip()
    ids=[str(x) for x in (payload.get("attachment_ids") or []) if str(x).strip()][:4]
    if not message and not ids: raise HTTPException(400,"message required")
    client_id=str(payload.get("client_message_id") or "")[:128]
    if client_id:
        receipt=storage.one("SELECT response_json FROM v2_chat_receipts WHERE account_id=? AND client_message_id=?",(aid,client_id))
        if receipt: return json.loads(receipt["response_json"])
    evidence,files=_evidence(aid,ids,message)
    youtube,sources=_youtube_research(aid,message)
    combined="\n\n---\n\n".join(x for x in (evidence,youtube) if x)[:30000]
    mind_message=("Use the supplied transcript/evidence to answer the user's request: "+message) if youtube else (message or "Please assess the attached material.")
    result=mind.process(aid,mind_message,combined)
    if result.get("web"):
        storage.execute(
            "INSERT INTO v2_research(account_id,mode,query,result,sources_json,useful,created_at) VALUES(?,?,?,?,?,?,?)",
            (aid,"foreground",message,str(result.get("reply") or "")[:20000],storage.jdump(result.get("sources") or []),None,storage.now()),
        )
    if sources and not result.get("sources"): result["sources"]=sources
    generated=images.maybe_explanatory_image(aid,message,str(result.get("reply") or ""))
    if generated:
        result["generated_image"]=generated
        result["image"]=generated
    result.update({"profile":account["username"],"client_message_id":client_id,"attachments":files,"attachment_grounding":bool(evidence),"research_grounding":bool(youtube or result.get("web"))})
    if client_id:
        storage.execute("INSERT OR REPLACE INTO v2_chat_receipts(account_id,client_message_id,response_json,created_at) VALUES(?,?,?,?)",(aid,client_id,json.dumps(result,ensure_ascii=False),storage.now()))
    return result
