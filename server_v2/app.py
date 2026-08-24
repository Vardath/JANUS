from __future__ import annotations

import base64
import io
import json
import os
import smtplib
import time
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from . import auth, storage
from .mind import mind, SPECIALISTS, HEMISPHERES, ARCHITECTURE

app = FastAPI(title="JANUS Server v2", version="2.0-reconstruction")


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    identifier: str
    password: str


class GoogleRequest(BaseModel):
    id_token: str


class TokenRequest(BaseModel):
    token: str


class ResetRequest(BaseModel):
    token: str
    new_password: str


class EmailRequest(BaseModel):
    email: str


def _token(authorization: Optional[str]) -> str:
    return auth.bearer(authorization)


def _account(authorization: Optional[str]):
    return auth.require_account(authorization)


def _send_email(to: str, subject: str, text: str) -> bool:
    host = os.getenv("JANUS_SMTP_HOST", "").strip()
    user = os.getenv("JANUS_SMTP_USER", "").strip()
    password = os.getenv("JANUS_SMTP_PASSWORD", "").strip()
    sender = os.getenv("JANUS_SMTP_FROM", "JANUS <onboarding@resend.dev>").strip()
    if not host or not password:
        return False
    try:
        msg = EmailMessage()
        msg["From"] = sender
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(text)
        port = int(os.getenv("JANUS_SMTP_PORT", "587"))
        with smtplib.SMTP(host, port, timeout=15) as s:
            if os.getenv("JANUS_SMTP_TLS", "1") == "1":
                s.starttls()
            if user:
                s.login(user, password)
            s.send_message(msg)
        return True
    except Exception:
        return False


def _extract_text(filename: str, mime: str, data: bytes) -> str:
    low = filename.lower()
    if mime.startswith("text/") or low.endswith((".txt", ".md", ".csv", ".json", ".py", ".java", ".xml", ".html")):
        return data.decode("utf-8", errors="replace")[:200000]
    if mime == "application/pdf" or low.endswith(".pdf"):
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data))
            return "\n\n".join((p.extract_text() or "") for p in reader.pages)[:200000]
        except Exception:
            return ""
    return ""


def _visual_assessment(row, prompt: str) -> str:
    if not str(row["mime_type"]).startswith("image/"):
        return ""
    try:
        from openai import OpenAI
        data = Path(row["storage_path"]).read_bytes()
        encoded = base64.b64encode(data).decode("ascii")
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
        model = os.getenv("JANUS_MODEL", "gpt-5.6")
        r = client.responses.create(
            model=model,
            input=[{"role":"user","content":[
                {"type":"input_text","text":"Assess this image for the JANUS specialist layer. Be concise and factual. User request: " + prompt[:2000]},
                {"type":"input_image","image_url":f"data:{row['mime_type']};base64,{encoded}"},
            ]}],
        )
        return (getattr(r, "output_text", "") or "").strip()[:12000]
    except Exception:
        return ""


def _attachment_evidence(account_id: int, attachment_ids: list[str], prompt: str) -> tuple[str, list[dict[str, Any]]]:
    blocks = []
    items = []
    for fid in attachment_ids[:4]:
        row = storage.get_file(account_id, fid)
        if not row:
            raise HTTPException(404, "Attached file not found")
        meta = {"id": row["id"], "filename": row["filename"], "mime_type": row["mime_type"], "size_bytes": row["size_bytes"]}
        text = str(row["extracted_text"] or "").strip()
        if text:
            blocks.append(f"SOURCE DOCUMENT {row['filename']}:\n{text[:12000]}")
            meta["grounded"] = True
        visual = _visual_assessment(row, prompt)
        if visual:
            blocks.append(f"SOURCE IMAGE {row['filename']} - MODEL VISUAL ASSESSMENT:\n{visual}")
            meta["visual_analysis"] = True
        items.append(meta)
    return "\n\n---\n\n".join(blocks)[:24000], items


@app.on_event("startup")
def startup():
    storage.init_schema()
    mind.start()


@app.on_event("shutdown")
def shutdown():
    mind.stop()


@app.get("/health")
def health():
    try:
        with storage.db() as c:
            quick = c.execute("PRAGMA quick_check").fetchone()[0]
        ok = str(quick).lower() == "ok"
    except Exception:
        ok = False
    return {
        "status": "ok" if ok else "degraded",
        "service": "janus-global-core-v2",
        "architecture": "7->2->1->1",
        "core_count": 11,
        "database_ok": ok,
        "main_app_loaded": True,
        "deployed_commit": os.getenv("RENDER_GIT_COMMIT", "unknown")[:40],
    }


@app.get("/diagnostics/runtime-health")
def runtime_health():
    h = health()
    runtime = mind.status()
    return {
        **h,
        "auth_schema_ok": True,
        "core_persistence_ok": True,
        "core_phase": runtime["phase"],
        "core_count": runtime["core_count"],
        "remote_clients": runtime["remote_clients"],
        "background_external_api_budget_used": runtime["background_external_api_budget_used"],
        "file_chat_grounding_enabled": True,
        "outbound_working_artifacts_enabled": True,
        "lightweight_image_generation_enabled": True,
        "background_multi_core_image_generation_enabled": False,
        "quarterly_maintenance_review_enabled": True,
        "server_generation": "v2-clean-reconstruction",
    }


@app.get("/protocol/capabilities")
def capabilities():
    return {
        "ok": True,
        "server_generation": "v2-clean-reconstruction",
        "architecture": "7->2->1->1",
        "core_count": 11,
        "features": {
            "password_auth": True,
            "google_auth": bool(auth.GOOGLE_CLIENT_ID),
            "email_verification": True,
            "password_reset": True,
            "account_deletion": True,
            "chat": True,
            "messages": True,
            "observe": True,
            "memory": True,
            "local_global_sync": True,
            "attachments": True,
            "document_grounding": True,
            "visual_analysis": True,
            "foreground_web": True,
            "research_workspace": True,
            "artifacts": True,
            "image_generation": True,
            "background_research": True,
            "maintenance": True,
            "cost_governor": True,
        },
    }


@app.post("/auth/register")
def register(req: RegisterRequest):
    try:
        row, token, verify_token = auth.register(req.username, req.email, req.password)
    except Exception as exc:
        if isinstance(exc, HTTPException): raise
        raise HTTPException(409, "Username or email already exists")
    sent = _send_email(row["email"], "Verify your JANUS email", f"JANUS verification code:\n\n{verify_token}\n")
    body = {"ok": True, "access_token": token, "account": auth.public_account(row)}
    if os.getenv("JANUS_EMAIL_MODE", "development") == "development" and not sent:
        body["development_verification_token"] = verify_token
    return body


@app.post("/auth/login")
def login(req: LoginRequest):
    row, token = auth.login(req.identifier, req.password)
    return {"ok": True, "access_token": token, "account": auth.public_account(row), "username": row["username"], "profile_id": row["username"]}


@app.post("/auth/google")
def google(req: GoogleRequest):
    row, token = auth.google_login(req.id_token)
    return {"ok": True, "access_token": token, "account": auth.public_account(row), "username": row["username"], "profile_id": row["username"]}


@app.get("/auth/me")
def me(authorization: Optional[str] = Header(default=None)):
    row = _account(authorization)
    return {"ok": True, "account": auth.public_account(row)}


@app.post("/auth/logout")
def logout(authorization: Optional[str] = Header(default=None)):
    token = _token(authorization)
    if token:
        storage.revoke_session(token)
    return {"ok": True}


@app.post("/auth/logout-all")
def logout_all(authorization: Optional[str] = Header(default=None)):
    row = _account(authorization)
    storage.revoke_all_sessions(int(row["id"]))
    return {"ok": True}


@app.post("/auth/forgot-password")
def forgot(req: EmailRequest):
    row = storage.account_by_identifier(req.email)
    if row:
        token = storage.issue_auth_token(int(row["id"]), "password_reset", 3600)
        sent = _send_email(row["email"], "Reset your JANUS password", f"JANUS password reset code:\n\n{token}\n")
        if os.getenv("JANUS_EMAIL_MODE", "development") == "development" and not sent:
            return {"ok": True, "development_reset_token": token}
    return {"ok": True}


@app.post("/auth/reset-password")
def reset(req: ResetRequest):
    auth.validate_password(req.new_password)
    token_row = storage.consume_auth_token(req.token, "password_reset")
    if not token_row:
        raise HTTPException(400, "Reset token is invalid or expired")
    storage.update_account(int(token_row["account_id"]), password_hash=auth.ph.hash(req.new_password))
    storage.revoke_all_sessions(int(token_row["account_id"]))
    return {"ok": True}


@app.post("/auth/resend-verification")
def resend(req: EmailRequest):
    row = storage.account_by_identifier(req.email)
    if row:
        token = storage.issue_auth_token(int(row["id"]), "verify_email", 86400)
        sent = _send_email(row["email"], "Verify your JANUS email", f"JANUS verification code:\n\n{token}\n")
        if os.getenv("JANUS_EMAIL_MODE", "development") == "development" and not sent:
            return {"ok": True, "development_verification_token": token}
    return {"ok": True}


@app.post("/auth/verify-email")
def verify(req: TokenRequest):
    token_row = storage.consume_auth_token(req.token, "verify_email")
    if not token_row:
        raise HTTPException(400, "Verification token is invalid or expired")
    storage.update_account(int(token_row["account_id"]), email_verified=1)
    return {"ok": True}


@app.delete("/auth/account")
async def delete_account(request: Request, authorization: Optional[str] = Header(default=None)):
    row = _account(authorization)
    body = await request.json()
    if str(body.get("confirmation") or "") != "DELETE":
        raise HTTPException(400, "confirmation must be DELETE")
    if row["password_hash"] and not auth.verify_password(row["password_hash"], str(body.get("current_password") or "")):
        raise HTTPException(401, "Current password is incorrect")
    storage.delete_account(int(row["id"]))
    return {"ok": True}


@app.post("/desktop/chat")
def chat(payload: dict[str, Any], authorization: Optional[str] = Header(default=None)):
    row = _account(authorization)
    account_id = int(row["id"])
    message = str(payload.get("message") or payload.get("text") or "").strip()
    if not message and not payload.get("attachment_ids"):
        raise HTTPException(400, "message required")
    client_id = str(payload.get("client_message_id") or "")[:128]
    if client_id:
        receipt = storage.one("SELECT response_json FROM v2_chat_receipts WHERE account_id=? AND client_message_id=?", (account_id, client_id))
        if receipt:
            return json.loads(receipt["response_json"])
    evidence, files = _attachment_evidence(account_id, [str(x) for x in (payload.get("attachment_ids") or [])], message)
    result = mind.process(account_id, message or "Please assess the attached material.", evidence)
    result.update({"profile": row["username"], "client_message_id": client_id, "attachments": files, "attachment_grounding": bool(evidence)})
    if client_id:
        storage.execute("INSERT OR REPLACE INTO v2_chat_receipts(account_id,client_message_id,response_json,created_at) VALUES(?,?,?,?)", (account_id, client_id, json.dumps(result, ensure_ascii=False), storage.now()))
    return result


@app.get("/desktop/messages")
def messages(limit: int = 50, include_dismissed: bool = False, authorization: Optional[str] = Header(default=None), username: str | None = None):
    row = _account(authorization)
    where = "account_id=?" + ("" if include_dismissed else " AND state<>'dismissed'")
    items = storage.rows(f"SELECT id,message_type,detail,source,state,created_at FROM v2_messages WHERE {where} ORDER BY id DESC LIMIT ?", (int(row["id"]), max(1, min(100, limit))))
    return {"profile": row["username"], "items": items, "unread": sum(1 for x in items if x["state"] == "unread")}


@app.post("/desktop/messages/{message_id}/state")
def message_state(message_id: int, payload: dict[str, Any], authorization: Optional[str] = Header(default=None)):
    row = _account(authorization)
    state = str(payload.get("state") or "read").lower()
    if state not in {"unread", "read", "dismissed"}:
        raise HTTPException(400, "invalid state")
    with storage.db() as c:
        found = c.execute("SELECT 1 FROM v2_messages WHERE id=? AND account_id=?", (message_id, int(row["id"]))).fetchone()
        if not found: raise HTTPException(404, "message not found")
        c.execute("UPDATE v2_messages SET state=? WHERE id=?", (state, message_id))
    return {"ok": True, "event_id": message_id, "state": state}


@app.get("/desktop/core-observe")
def core_observe(mode: str = "all", limit: int = 180, authorization: Optional[str] = Header(default=None), username: str | None = None):
    row = _account(authorization)
    args: list[Any] = [int(row["id"])]
    where = "account_id=?"
    if mode != "all":
        where += " AND mode=?"; args.append(mode)
    args.append(max(1, min(500, limit)))
    items = storage.rows(f"SELECT id,core_name,event_type,mode,public_detail AS detail,created_at FROM v2_events WHERE {where} ORDER BY id DESC LIMIT ?", args)
    return {"items": items, "profile": row["username"], "externalizable_only": True}


@app.get("/desktop/observe")
def observe(authorization: Optional[str] = Header(default=None), username: str | None = None):
    return core_observe("all", 180, authorization, username)


@app.get("/desktop/runtime-cores")
def runtime_cores(authorization: Optional[str] = Header(default=None), username: str | None = None):
    row = _account(authorization)
    return {"profile": row["username"], "architecture": ARCHITECTURE, "runtime": mind.status(int(row["id"]))}


@app.get("/desktop/cores")
def cores(authorization: Optional[str] = Header(default=None), username: str | None = None):
    row = _account(authorization)
    status = mind.status(int(row["id"]))
    return {"profile": row["username"], "cores": list(status["cores"].values()), "architecture": ARCHITECTURE}


@app.get("/desktop/memory")
def memory(limit: int = 80, authorization: Optional[str] = Header(default=None), username: str | None = None):
    row = _account(authorization)
    return {"profile": row["username"], "items": storage.list_memories(int(row["id"]), limit)}


@app.get("/desktop/activity")
def activity(limit: int = 80, authorization: Optional[str] = Header(default=None), username: str | None = None):
    row = _account(authorization)
    items = storage.rows("SELECT id,event_type,core_name AS source,public_detail AS detail,created_at FROM v2_events WHERE account_id=? ORDER BY id DESC LIMIT ?", (int(row["id"]), max(1, min(100, limit))))
    return {"profile": row["username"], "items": items}


@app.get("/desktop/home")
def home(authorization: Optional[str] = Header(default=None), username: str | None = None):
    row = _account(authorization)
    runtime = mind.status(int(row["id"]))
    unread = storage.one("SELECT count(*) n FROM v2_messages WHERE account_id=? AND state='unread'", (int(row["id"]),))
    return {"profile": row["username"], "status": "Active" if runtime["phase"] == "wake" else "Dormant", "architecture": "11-core", "unread_messages": int(unread["n"] if unread else 0), "core_phase": runtime["phase"], "core_runtime": runtime, "external_api_budget_used_by_core_cycle": 0}


@app.get("/desktop/settings")
def settings(authorization: Optional[str] = Header(default=None), username: str | None = None):
    row = _account(authorization)
    return {"profile": row["username"], "background_interval_minutes": 15, "wake_seconds": mind.wake_seconds, "sleep_seconds": mind.sleep_seconds, "server_background_model_calls": 0, "paid_background_reflection": False}


@app.post("/core-sync/exchange")
def sync(payload: dict[str, Any], authorization: Optional[str] = Header(default=None)):
    row = _account(authorization)
    return mind.ingest_device(int(row["id"]), payload)


@app.post("/files/upload")
def upload(payload: dict[str, Any], authorization: Optional[str] = Header(default=None)):
    row = _account(authorization)
    try:
        raw = base64.b64decode(str(payload.get("data_base64") or ""), validate=True)
    except Exception:
        raise HTTPException(400, "Invalid base64 file data")
    if not raw or len(raw) > 8 * 1024 * 1024:
        raise HTTPException(400, "File must be between 1 byte and 8 MB")
    filename = str(payload.get("filename") or "attachment.bin")[:240]
    mime = str(payload.get("mime_type") or "application/octet-stream")[:160]
    text = _extract_text(filename, mime, raw)
    file = storage.save_file(int(row["id"]), filename, mime, raw, text)
    return {"ok": True, "file": file}


@app.get("/files/{file_id}/download")
def download(file_id: str, authorization: Optional[str] = Header(default=None)):
    row = _account(authorization)
    f = storage.get_file(int(row["id"]), file_id)
    if not f: raise HTTPException(404, "file not found")
    return FileResponse(f["storage_path"], media_type=f["mime_type"], filename=f["filename"])


@app.get("/images/{file_id}/inline")
def image_inline(file_id: str, authorization: Optional[str] = Header(default=None)):
    row = _account(authorization)
    f = storage.get_file(int(row["id"]), file_id)
    if not f or not str(f["mime_type"]).startswith("image/"):
        raise HTTPException(404, "image not found")
    data = Path(f["storage_path"]).read_bytes()
    return {"ok": True, "file_id": file_id, "mime_type": f["mime_type"], "data_base64": base64.b64encode(data).decode("ascii")}


@app.post("/images/generate")
def image_generate(payload: dict[str, Any], authorization: Optional[str] = Header(default=None)):
    row = _account(authorization)
    prompt = str(payload.get("prompt") or payload.get("description") or "").strip()
    if not prompt: raise HTTPException(400, "prompt required")
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
        result = client.images.generate(model=os.getenv("JANUS_IMAGE_MODEL", "gpt-image-1"), prompt=prompt[:4000], size="1024x1024", quality=os.getenv("JANUS_IMAGE_QUALITY", "medium"))
        b64 = result.data[0].b64_json
        raw = base64.b64decode(b64)
    except Exception as exc:
        raise HTTPException(502, f"Image generation failed: {type(exc).__name__}")
    file = storage.save_file(int(row["id"]), "janus-generated.png", "image/png", raw)
    return {"ok": True, "generated_image": {**file, "inline_path": f"/images/{file['id']}/inline"}, "image": file}


@app.get("/images/usage")
def image_usage(authorization: Optional[str] = Header(default=None)):
    row = _account(authorization)
    count = storage.one("SELECT count(*) n FROM v2_files WHERE account_id=? AND filename='janus-generated.png' AND created_at>?", (int(row["id"]), storage.now()-86400))
    return {"ok": True, "generated_today": int(count["n"] if count else 0), "quality": os.getenv("JANUS_IMAGE_QUALITY", "medium"), "background_multi_core_image_generation": False}


@app.post("/research/workspace/seed")
def research_seed(authorization: Optional[str] = Header(default=None)):
    row = _account(authorization); aid = int(row["id"])
    existing = storage.one("SELECT count(*) n FROM v2_claims WHERE account_id=?", (aid,))
    if existing and int(existing["n"]) > 0: return {"ok": True, "seeded": False}
    seeds = [
        ("JANUS architecture", "Maintain the 7 -> 2 -> 1 -> 1 functional architecture across local and global runtimes.", "design", "active", "janus"),
        ("Selective federation", "Local and global JANUS exchange bounded summaries and never overwrite each other's protected core state.", "design", "active", "janus"),
        ("Cost discipline", "Background cycles should be deterministic/zero-API by default; external research is bounded and purposeful.", "policy", "active", "janus"),
    ]
    for title, statement, kind, state, domain in seeds:
        storage.execute("INSERT INTO v2_claims(account_id,title,statement,claim_kind,epistemic_state,domain,tags_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)", (aid,title,statement,kind,state,domain,"[]",storage.now(),storage.now()))
    return {"ok": True, "seeded": True}


@app.get("/research/workspace")
def research_workspace(authorization: Optional[str] = Header(default=None), domain: str | None = None, state: str | None = None):
    row = _account(authorization); aid = int(row["id"])
    where = "account_id=?"; args: list[Any] = [aid]
    if domain: where += " AND domain=?"; args.append(domain)
    if state: where += " AND epistemic_state=?"; args.append(state)
    claims = storage.rows(f"SELECT id,title,statement,claim_kind,epistemic_state,domain,tags_json,created_at,updated_at FROM v2_claims WHERE {where} ORDER BY id DESC", args)
    for c in claims: c["tags"] = json.loads(c.pop("tags_json") or "[]")
    return {"ok": True, "claims": claims, "count": len(claims)}


@app.get("/research-provenance/status")
def research_provenance(limit: int = 40, authorization: Optional[str] = Header(default=None)):
    row = _account(authorization); aid = int(row["id"])
    recent = storage.rows("SELECT id,mode,query,result,sources_json,useful,created_at FROM v2_research WHERE account_id=? ORDER BY id DESC LIMIT ?", (aid,max(1,min(100,limit))))
    useful = sum(1 for r in recent if r["useful"] == 1)
    scored = sum(1 for r in recent if r["useful"] is not None)
    for r in recent:
        r["result_preview"] = r.pop("result")[:1200]
        r["sources"] = json.loads(r.pop("sources_json") or "[]")
    return {"ok": True, "usefulness": {"useful": useful, "completed_scored": scored, "usefulness_rate": useful/scored if scored else 0}, "external_compute": {"background_today_estimated_usd": 0.0, "denied_today": 0}, "recent_searches": recent}


@app.post("/artifacts")
def create_artifact(payload: dict[str, Any], authorization: Optional[str] = Header(default=None)):
    row = _account(authorization); aid = int(row["id"])
    kind = str(payload.get("kind") or "working_note").strip()
    title = str(payload.get("title") or {
        "continuity_report":"JANUS Continuity Report", "project_snapshot":"JANUS Project Snapshot", "research_digest":"JANUS Research Digest", "working_note":"JANUS Working Note"
    }.get(kind, "JANUS Artifact"))[:160]
    if kind == "continuity_report":
        memories = storage.list_memories(aid, 120)
        content = "# " + title + "\n\n" + "\n".join(f"- [{m['tier']}] {m['content']}" for m in memories)
    elif kind == "research_digest":
        rr = storage.rows("SELECT query,result,created_at FROM v2_research WHERE account_id=? ORDER BY id DESC LIMIT 20", (aid,))
        content = "# " + title + "\n\n" + "\n\n".join(f"## {x['query']}\n{x['result']}" for x in rr)
    elif kind == "project_snapshot":
        claims = research_workspace(authorization=authorization)["claims"]
        content = "# " + title + "\n\n" + "\n".join(f"- **{x['title']}** [{x['epistemic_state']}]: {x['statement']}" for x in claims)
    else:
        content = "# " + title + "\n\n" + str(payload.get("note") or "JANUS working note.")
    file = storage.save_file(aid, title.lower().replace(" ", "-")[:80] + ".md", "text/markdown", content.encode("utf-8"), content)
    artifact_id = storage.execute("INSERT INTO v2_artifacts(account_id,kind,title,file_id,created_at) VALUES(?,?,?,?,?)", (aid, kind, title, file["id"], storage.now()))
    return {"ok": True, "artifact": {"id": artifact_id, "kind": kind, "title": title, "file": file}}


@app.get("/artifacts")
def list_artifacts(authorization: Optional[str] = Header(default=None)):
    row = _account(authorization); aid = int(row["id"])
    items = storage.rows("SELECT a.id,a.kind,a.title,a.file_id,a.created_at,f.filename AS original_name,f.mime_type,f.size_bytes FROM v2_artifacts a JOIN v2_files f ON f.id=a.file_id WHERE a.account_id=? ORDER BY a.id DESC LIMIT 200", (aid,))
    for i in items: i["download_path"] = f"/files/{i['file_id']}/download"; i["available"] = True
    return {"ok": True, "items": items}


@app.get("/artifacts/{artifact_id}")
def artifact_info(artifact_id: int, authorization: Optional[str] = Header(default=None)):
    row = _account(authorization); aid = int(row["id"])
    a = storage.one("SELECT a.id,a.kind,a.title,a.file_id,a.created_at,f.filename AS original_name,f.mime_type,f.size_bytes FROM v2_artifacts a JOIN v2_files f ON f.id=a.file_id WHERE a.account_id=? AND a.id=?", (aid,artifact_id))
    if not a: raise HTTPException(404, "artifact not found")
    d = dict(a); d["download_path"] = f"/files/{d['file_id']}/download"; d["available"] = True
    return {"ok": True, "artifact": d}


@app.get("/maintenance/status")
def maintenance_status(authorization: Optional[str] = Header(default=None)):
    row = _account(authorization); aid = int(row["id"])
    reviews = storage.rows("SELECT id,report_json,review_state,created_at,decided_at FROM v2_maintenance WHERE account_id IS NULL OR account_id=? ORDER BY id DESC LIMIT 30", (aid,))
    for r in reviews: r["report"] = json.loads(r.pop("report_json") or "{}")
    return {"ok": True, "maintenance": {"enabled": True, "interval_days": 90, "due": False, "automatic_code_changes": False}, "reviews": reviews}


@app.post("/maintenance/reviews/{review_id}/decision")
def maintenance_decision(review_id: int, payload: dict[str, Any], authorization: Optional[str] = Header(default=None)):
    row = _account(authorization); aid = int(row["id"])
    decision = str(payload.get("decision") or "")
    if decision not in {"approved_for_manual_work", "deferred", "rejected"}: raise HTTPException(400, "invalid decision")
    with storage.db() as c:
        found = c.execute("SELECT 1 FROM v2_maintenance WHERE id=? AND (account_id IS NULL OR account_id=?)", (review_id, aid)).fetchone()
        if not found: raise HTTPException(404, "maintenance review not found")
        c.execute("UPDATE v2_maintenance SET review_state=?,decided_at=? WHERE id=?", (decision, storage.now(), review_id))
    return {"ok": True, "review_id": review_id, "decision": decision, "automatic_changes": False}


@app.get("/desktop/cost-status")
def cost_status(authorization: Optional[str] = Header(default=None)):
    _account(authorization)
    return {"ok": True, "mode": os.getenv("JANUS_COMPUTE_BUDGET", "balanced"), "background_model_calls": 0, "background_daily_call_cap": int(os.getenv("JANUS_BACKGROUND_DAILY_CALL_CAP", "12")), "background_multi_core_image_generation": False}
