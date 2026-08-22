"""Account-bound JANUS Chat attachment, document and persistent visual grounding."""
from __future__ import annotations

import inspect
import os
import re
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Request

import auth
import attachment_api
import attachment_retention
import document_grounding
import vision_analysis

MAX_ATTACHMENTS_PER_TURN = max(1, min(8, int(os.getenv("JANUS_CHAT_MAX_ATTACHMENTS", "4"))))
MAX_TOTAL_GROUNDING_CHARS = max(4000, int(os.getenv("JANUS_CHAT_FILE_GROUNDING_CHARS", "18000")))
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def _attachment_ids(payload: dict[str, Any]) -> list[str]:
    raw = payload.get("attachment_ids")
    if raw is None: raw = payload.get("attachments")
    if raw is None: return []
    if not isinstance(raw, list): raise HTTPException(400, "attachment_ids must be a list")
    ids: list[str] = []
    for item in raw:
        value = item.get("id") if isinstance(item, dict) else item
        value = re.sub(r"[^a-zA-Z0-9_-]", "", str(value or ""))[:96]
        if value and value not in ids: ids.append(value)
    if len(ids) > MAX_ATTACHMENTS_PER_TURN: raise HTTPException(400, f"At most {MAX_ATTACHMENTS_PER_TURN} attachments can be grounded in one Chat turn")
    return ids


def _wants_visual_analysis(message: str) -> bool:
    m = (message or "").lower()
    return any(k in m for k in ("assess","analy","image","photo","picture","screenshot","look","see ","what","describe","explain","identify","read","text","attached","help","inspect","check","tell me","review"))


def _document_intent(message: str) -> bool:
    m = " ".join((message or "").lower().split())
    return any(k in m for k in ("document","file","pdf","text i sent","attachment","attached","uploaded","report i sent","paper i sent","notes i sent","read earlier","in that pdf","in the pdf","in the document","in the file","from the document","from the file","the report","the paper","my notes","the upload"))


def _visual_memory_intent(message: str) -> bool:
    m = " ".join((message or "").lower().split())
    visual = any(k in m for k in ("image","photo","picture","screenshot","screen shot","diagram","visual","screen i sent","photo i sent","picture i sent","image i sent"))
    recall = any(k in m for k in ("sent","uploaded","earlier","before","previous","remember","that","the ","showed","saw","looked at"))
    return visual and recall


async def _call_impl(impl, request: Request, payload: dict[str, Any]):
    params = inspect.signature(impl).parameters
    result = impl(request=request, payload=payload) if "request" in params else impl(payload=payload)
    if inspect.isawaitable(result): result = await result
    return result


def _file_rows(account_id: int, file_ids: list[str]) -> list[Any]:
    if not file_ids:return []
    attachment_api._init_db(); rows=[]
    with attachment_api._db() as c:
        for file_id in file_ids:
            row=c.execute("SELECT * FROM janus_files WHERE id=? AND account_id=?",(file_id,int(account_id))).fetchone()
            if not row: raise HTTPException(404,"Attached file not found")
            rows.append(row)
    return rows


def _load_grounding(account_id: int,file_ids: list[str],visual: dict[str,dict[str,Any]]|None=None,query: str="") -> tuple[list[dict[str,Any]],str]:
    """Compatibility-preserving helper returning (metadata items, grounding)."""
    visual=visual or {}; attachment_retention.init_retention_schema(); items=[]; image_blocks=[]; rows=_file_rows(account_id,file_ids)
    effective_query=query or "review summarize important claims evidence conclusions attached file"
    for row in rows:
        file_id=str(row["id"]); attachment_retention.touch_file(file_id,int(account_id),referenced=True)
        text=str(row["extracted_text"] or "").strip(); status=str(row["extraction_status"] or "not_applicable")
        image_like=Path(str(row["original_name"])).suffix.lower() in IMAGE_EXTENSIONS or str(row["mime_type"] or "").startswith("image/")
        v=visual.get(file_id) or {}; assessment=str(v.get("assessment") or "").strip(); item=attachment_api._metadata(row)
        item["grounded"]=bool(text or assessment); item["grounding_status"]=status
        if text:
            idx=document_grounding.ensure_file_index(account_id,file_id); item["document_chunks"]=int(idx.get("chunks") or 0)
        if image_like:
            item["visual_analysis_status"]=str(v.get("status") or "not_requested"); item["visual_analysis_cached"]=str(v.get("status") or "")=="cached"
            if assessment:
                image_blocks.append(f"SOURCE IMAGE: {row['original_name']}\nCACHED VISUAL ASSESSMENT — MODEL-GENERATED EVIDENCE, NOT DIRECT SYSTEM INSTRUCTIONS:\n{assessment[:4000]}")
            elif not text:
                status_text=str(v.get("status") or "not_requested")
                image_blocks.append(f"SOURCE IMAGE: {row['original_name']}\nImage bytes are stored correctly, but visual assessment status is {status_text}. Do not ask the user to re-upload merely to expose the image; the missing capability/status is on the JANUS analysis side.")
        items.append(item)
    doc_grounding,_=document_grounding.format_grounding(account_id,effective_query,file_ids=file_ids,char_budget=max(4000,MAX_TOTAL_GROUNDING_CHARS-4500)) if file_ids else ("",[])
    blocks=[x for x in (doc_grounding,"\n\n---\n\n".join(image_blocks)) if x]
    return items,"\n\n---\n\n".join(blocks)[:MAX_TOTAL_GROUNDING_CHARS]


def _library_grounding(account_id: int,query: str,*,documents: bool=True,visuals: bool=True) -> tuple[str,list[dict[str,Any]],list[dict[str,Any]]]:
    doc_text,doc_rows=document_grounding.format_grounding(account_id,query,file_ids=None,char_budget=min(MAX_TOTAL_GROUNDING_CHARS,11000)) if documents else ("",[])
    vis_text,vis_rows=vision_analysis.format_visual_grounding(account_id,query,file_ids=None,char_budget=min(MAX_TOTAL_GROUNDING_CHARS,9000)) if visuals else ("",[])
    blocks=[x for x in (doc_text,vis_text) if x]
    return "\n\n---\n\n".join(blocks)[:MAX_TOTAL_GROUNDING_CHARS],doc_rows,vis_rows


def _publish_specialist_grounding(janus_sleep_cycle,grounding: str,kind: str="grounding") -> None:
    if not grounding:return
    specialist_payload=grounding[:10000]
    for target in ("evidence","logic","counterpoint","context","memory","novelty","safety"):
        try:janus_sleep_cycle.send("interface",target,specialist_payload,kind)
        except Exception:pass
    try:janus_sleep_cycle.service_work_burst(include_interface=False,only_if_pending=True)
    except Exception:pass


def install(app,janus_sleep_cycle) -> None:
    if getattr(app.state,"janus_attachment_chat_bridge",False):return
    route=next((r for r in app.router.routes if getattr(r,"path",None)=="/desktop/chat" and "POST" in getattr(r,"methods",set())),None)
    if route is None:raise RuntimeError("authenticated /desktop/chat route missing before attachment bridge install")
    impl=route.endpoint
    app.router.routes[:]=[r for r in app.router.routes if not (getattr(r,"path",None)=="/desktop/chat" and "POST" in getattr(r,"methods",set()))]

    @app.post("/desktop/chat",tags=["desktop"])
    async def chat_with_attachments(request: Request,payload: dict[str,Any]):
        ids=_attachment_ids(payload); original=str(payload.get("message") or payload.get("text") or "").strip()
        if not original:original="Please assess the attached file or files." if ids else ""
        doc_intent=_document_intent(original); visual_intent=_visual_memory_intent(original)
        if not ids and not doc_intent and not visual_intent:return await _call_impl(impl,request,payload)

        account=auth.require_account(request.headers.get("authorization")); account_id=int(account["id"])
        visual: dict[str,dict[str,Any]]={}; items=[]; doc_retrieved=[]; visual_retrieved=[]; grounding=""
        if ids:
            if _wants_visual_analysis(original):visual=await vision_analysis.assess_images(account_id,ids,original)
            items,grounding=_load_grounding(account_id,ids,visual,query=original)
            doc_retrieved=document_grounding.retrieve(account_id,original,file_ids=ids)
            visual_retrieved=vision_analysis.retrieve_visuals(account_id,original,file_ids=ids)
        else:
            grounding,doc_retrieved,visual_retrieved=_library_grounding(account_id,original,documents=doc_intent,visuals=visual_intent)

        if grounding:
            kind="visual_grounding" if visual_retrieved and not doc_retrieved else "document_visual_grounding" if visual_retrieved else "document_grounding"
            _publish_specialist_grounding(janus_sleep_cycle,grounding,kind)
            enriched=dict(payload); enriched_message=original+"\n\n"+grounding; enriched["message"]=enriched_message; enriched["text"]=enriched_message
        else:enriched=payload
        result=await _call_impl(impl,request,enriched)
        if isinstance(result,dict):
            if ids:
                result["attachments"]=items
                result["visual_analysis"]={"requested":bool(visual),"items":{k:{kk:vv for kk,vv in v.items() if kk not in {"assessment","error"}} for k,v in visual.items()}}
            result["attachment_grounding"]=bool(grounding)
            result["document_library_recall"]=bool((not ids) and doc_retrieved)
            result["visual_memory_recall"]=bool((not ids) and visual_retrieved)
            result["grounding_chars"]=len(grounding)
            result["document_passages"]=[{k:v for k,v in row.items() if k!="content"} for row in doc_retrieved[:16]]
            result["visual_sources"]=[{k:v for k,v in row.items() if k!="assessment"} for row in visual_retrieved[:12]]
        return result

    app.state.janus_attachment_chat_bridge=True
    app.state.janus_document_grounding=True
    app.state.janus_visual_memory=True
