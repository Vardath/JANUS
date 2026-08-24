from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException

from . import auth, diagnostics, governance, images, media, sensory_bus, storage, visual_memory
from .mind import mind

router = APIRouter()


def _visual_assessment(account_id: int, row, prompt: str) -> str:
    cached = visual_memory.get(account_id, str(row["id"]))
    if cached:
        text = str(cached["assessment"])
        if text:
            sensory_bus.ingest(
                account_id, "image", f"visual_memory:{row['filename']}", text,
                salience=0.72, uncertainty=0.28, novelty=0.3,
                metadata={"file_id": str(row["id"]), "cached": True, "mime_type": str(row["mime_type"])},
                mode="foreground",
            )
        return text
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
            sensory_bus.ingest(
                account_id, "image", f"vision:{row['filename']}", text,
                salience=0.82, uncertainty=0.3, novelty=0.68,
                metadata={"file_id": str(row["id"]), "cached": False, "mime_type": str(row["mime_type"]), "model": model},
                mode="foreground",
            )
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
            sensory_bus.ingest(
                account_id, "file", f"attachment:{row['filename']}", text[:12000],
                salience=0.8, uncertainty=0.25, novelty=0.45,
                metadata={"file_id": str(row["id"]), "filename": str(row["filename"]), "mime_type": str(row["mime_type"]), "size_bytes": int(row["size_bytes"])},
                mode="foreground",
            )
        elif not str(row["mime_type"]).startswith("image/"):
            sensory_bus.ingest(
                account_id, "file", f"attachment:{row['filename']}",
                f"File attached without extractable text: {row['filename']} ({row['mime_type']}, {row['size_bytes']} bytes).",
                salience=0.58, uncertainty=0.62, novelty=0.4,
                metadata={"file_id": str(row["id"]), "filename": str(row["filename"]), "mime_type": str(row["mime_type"]), "size_bytes": int(row["size_bytes"])},
                mode="foreground",
            )
        assessment=_visual_assessment(account_id,row,message)
        if assessment:
            blocks.append(f"SOURCE IMAGE {row['filename']} — PERSISTED VISUAL ASSESSMENT:\n{assessment[:12000]}")
            meta["visual_analysis"]=True
        files.append(meta)
    lower=message.lower()
    if not ids and any(x in lower for x in ("image i sent","photo i sent","picture i sent","screenshot i sent","previous image","earlier image","that image","that photo")):
        prior=visual_memory.retrieve(account_id,message,5)
        for x in prior:
            assessment = str(x['assessment'])[:6000]
            blocks.append(f"RECALLED VISUAL MEMORY {x['filename']}:\n{assessment}")
            sensory_bus.ingest(
                account_id, "memory", f"visual_memory:{x['filename']}", assessment,
                salience=0.62, uncertainty=0.36, novelty=0.22,
                metadata={"filename": str(x['filename']), "recalled_visual": True},
                mode="foreground",
            )
    return "\n\n---\n\n".join(blocks)[:26000],files


def _youtube_research(account_id: int, message: str) -> tuple[str,list[dict[str,str]]]:
    transcript=media.youtube_transcript(message)
    if transcript["matched"] and transcript["text"]:
        source=[transcript["source"]] if transcript["source"] else []
        text="YouTube transcript retrieved:\n"+transcript["text"]
        storage.execute("INSERT INTO v2_research(account_id,mode,query,result,sources_json,useful,created_at) VALUES(?,?,?,?,?,?,?)",(account_id,"foreground_youtube",message,text,storage.jdump(source),None,storage.now()))
        sensory_bus.ingest(
            account_id, "audio", "youtube_transcript", transcript["text"][:12000],
            salience=0.76, uncertainty=0.38, novelty=0.58,
            metadata={"source": transcript.get("source"), "transcript": True},
            mode="foreground",
        )
        return text,source
    return "",[]


@router.post("/desktop/chat")
def chat(payload: dict[str,Any], authorization: Optional[str]=Header(default=None)):
    account=auth.require_account(authorization); aid=int(account["id"])
    message=str(payload.get("message") or payload.get("text") or "").strip()
    visible_message=str(payload.get("user_visible_message") or message).strip()
    ids=[str(x) for x in (payload.get("attachment_ids") or []) if str(x).strip()][:4]
    if not message and not ids: raise HTTPException(400,"message required")
    client_id=str(payload.get("client_message_id") or "")[:128]
    if client_id:
        receipt=storage.one("SELECT response_json FROM v2_chat_receipts WHERE account_id=? AND client_message_id=?",(aid,client_id))
        if receipt: return json.loads(receipt["response_json"])
    evidence,files=_evidence(aid,ids,visible_message)
    youtube,sources=_youtube_research(aid,visible_message)
    combined="\n\n---\n\n".join(x for x in (evidence,youtube) if x)[:30000]
    mind_message=("Use the supplied transcript/evidence to answer the user's request: "+message) if youtube else (message or "Please assess the attached material.")
    result=mind.process(aid,mind_message,combined)
    if result.get("web"):
        web_sources = result.get("sources") or []
        storage.execute(
            "INSERT INTO v2_research(account_id,mode,query,result,sources_json,useful,created_at) VALUES(?,?,?,?,?,?,?)",
            (aid,"foreground",visible_message,str(result.get("reply") or "")[:20000],storage.jdump(web_sources),None,storage.now()),
        )
        sensory_bus.ingest(
            aid, "web", "foreground_web",
            "Live web research contributed to this turn. Query: " + visible_message[:1800] + " Sources: " + ", ".join(str(x.get("url") or x.get("title") or "") for x in web_sources[:8]),
            salience=0.78, uncertainty=0.34, novelty=0.66,
            metadata={"source_count": len(web_sources), "query": visible_message[:500]},
            mode="foreground",
        )
    if sources and not result.get("sources"): result["sources"]=sources
    generated=images.maybe_explanatory_image(aid,visible_message,str(result.get("reply") or ""))
    if generated:
        result["generated_image"]=generated
        result["image"]=generated
    result.update({"profile":account["username"],"client_message_id":client_id,"attachments":files,"attachment_grounding":bool(evidence),"research_grounding":bool(youtube or result.get("web"))})

    # Externalizable self-diagnosis: preserve the visible user turn, inspect only the
    # returned/interface result and explicit capability-request metadata. This is not
    # private chain-of-thought and never authorizes JANUS to modify itself.
    diagnostics.record_chat_turn(aid, visible_message, str(result.get("reply") or ""), client_id)
    findings = diagnostics.inspect_chat(aid, visible_message, result)
    if findings:
        result["diagnostic_requests_recorded"] = [int(x.get("id") or 0) for x in findings]
        result["supervisor_review_queued"] = True

    if client_id:
        storage.execute("INSERT OR REPLACE INTO v2_chat_receipts(account_id,client_message_id,response_json,created_at) VALUES(?,?,?,?)",(aid,client_id,json.dumps(result,ensure_ascii=False),storage.now()))
    return result
