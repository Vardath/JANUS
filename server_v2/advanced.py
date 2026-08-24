from __future__ import annotations

import json
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException, Query

from . import auth, governance, storage

router = APIRouter()


def account(authorization: Optional[str]):
    return auth.require_account(authorization)


@router.get("/reliability/status")
def reliability_status(authorization: Optional[str] = Header(default=None)):
    a = account(authorization); aid = int(a["id"])
    return {
        "ok": True,
        "meaning": "Historical downstream consistency/calibration; not objective truth.",
        "cores": governance.reliability(aid),
        "bridge_authority": governance.bridge_authority(aid),
        "authority_bounds": [0.2, 0.8],
    }


@router.get("/desktop/continuity")
def continuity_list(open_only: bool = Query(default=False), limit: int = Query(default=100, ge=1, le=200), authorization: Optional[str] = Header(default=None)):
    a = account(authorization)
    return {"profile": a["username"], "items": governance.continuity_list(int(a["id"]), open_only, limit)}


@router.post("/desktop/continuity")
def continuity_create(payload: dict[str, Any], authorization: Optional[str] = Header(default=None)):
    a = account(authorization)
    title = str(payload.get("title") or "").strip()
    if not title: raise HTTPException(400, "title required")
    item = governance.continuity_create(
        int(a["id"]), title, str(payload.get("detail") or ""), str(payload.get("kind") or "thread"),
        int(payload.get("priority") or 50), payload.get("tags") if isinstance(payload.get("tags"), list) else [],
    )
    return {"ok": True, "item": item}


@router.post("/desktop/continuity/{item_id}/state")
def continuity_set_state(item_id: int, payload: dict[str, Any], authorization: Optional[str] = Header(default=None)):
    a = account(authorization)
    try:
        item = governance.continuity_state(int(a["id"]), item_id, str(payload.get("state") or ""), str(payload.get("note") or ""))
    except KeyError: raise HTTPException(404, "continuity item not found")
    except ValueError as exc: raise HTTPException(400, str(exc))
    return {"ok": True, "item": item}


@router.get("/desktop/continuity/{item_id}/events")
def continuity_events(item_id: int, authorization: Optional[str] = Header(default=None)):
    a = account(authorization)
    try: governance.continuity_get(int(a["id"]), item_id)
    except KeyError: raise HTTPException(404, "continuity item not found")
    items = storage.rows("SELECT id,event_type,old_state,new_state,note,created_at FROM v2_continuity_events WHERE item_id=? ORDER BY id DESC LIMIT 200", (item_id,))
    return {"ok": True, "items": items}


@router.post("/claims")
def claim_create(payload: dict[str, Any], authorization: Optional[str] = Header(default=None)):
    a = account(authorization); aid = int(a["id"])
    title = str(payload.get("title") or "").strip(); statement = str(payload.get("statement") or "").strip()
    if not title or not statement: raise HTTPException(400, "title and statement required")
    ts = storage.now()
    claim_id = storage.execute(
        "INSERT INTO v2_claims(account_id,title,statement,claim_kind,epistemic_state,domain,tags_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
        (aid,title[:180],statement[:12000],str(payload.get("claim_kind") or "hypothesis")[:80],str(payload.get("epistemic_state") or "open")[:80],str(payload.get("domain") or "general")[:120],json.dumps(payload.get("tags") or []),ts,ts),
    )
    row = storage.one("SELECT * FROM v2_claims WHERE id=? AND account_id=?", (claim_id,aid))
    return {"ok": True, "claim": dict(row)}


@router.post("/claims/{claim_id}/evidence")
def claim_evidence(claim_id: int, payload: dict[str, Any], authorization: Optional[str] = Header(default=None)):
    a = account(authorization); aid = int(a["id"])
    claim = storage.one("SELECT 1 FROM v2_claims WHERE id=? AND account_id=?", (claim_id,aid))
    if not claim: raise HTTPException(404, "claim not found")
    summary = str(payload.get("summary") or "").strip()
    if not summary: raise HTTPException(400, "summary required")
    eid = storage.execute("INSERT INTO v2_claim_evidence(claim_id,account_id,evidence_kind,summary,source_uri,result,created_at) VALUES(?,?,?,?,?,?,?)", (claim_id,aid,str(payload.get("evidence_kind") or "observation")[:80],summary[:12000],str(payload.get("source_uri") or "")[:2000],str(payload.get("result") or "")[:12000],storage.now()))
    return {"ok": True, "evidence": {"id":eid,"claim_id":claim_id,"summary":summary}}


@router.get("/claims/{claim_id}/evidence")
def claim_evidence_list(claim_id: int, authorization: Optional[str] = Header(default=None)):
    a = account(authorization); aid = int(a["id"])
    claim = storage.one("SELECT 1 FROM v2_claims WHERE id=? AND account_id=?", (claim_id,aid))
    if not claim: raise HTTPException(404, "claim not found")
    return {"ok": True, "items": storage.rows("SELECT id,evidence_kind,summary,source_uri,result,created_at FROM v2_claim_evidence WHERE claim_id=? AND account_id=? ORDER BY id DESC", (claim_id,aid))}


@router.get("/background-usefulness/status")
def background_usefulness(authorization: Optional[str] = Header(default=None)):
    a = account(authorization); aid = int(a["id"])
    rows = storage.rows("SELECT useful,count(*) n FROM v2_research WHERE account_id=? GROUP BY useful", (aid,))
    useful = sum(int(x["n"]) for x in rows if x["useful"] == 1)
    scored = sum(int(x["n"]) for x in rows if x["useful"] is not None)
    return {"ok": True, "useful":useful, "completed_scored":scored, "usefulness_rate":useful/scored if scored else 0.0}


@router.get("/visual-deliberations")
def visual_deliberations(authorization: Optional[str] = Header(default=None)):
    a = account(authorization); aid = int(a["id"])
    items = storage.rows("SELECT id,event_type,public_detail AS summary,created_at FROM v2_events WHERE account_id=? AND event_type IN ('visual_assessment','visual_deliberation') ORDER BY id DESC LIMIT 50", (aid,))
    return {"ok": True, "items": items, "background_multi_core_image_generation": False}


@router.get("/desktop/message-quality")
def message_quality(authorization: Optional[str] = Header(default=None)):
    a = account(authorization); aid = int(a["id"])
    total = storage.one("SELECT count(*) n FROM v2_messages WHERE account_id=?", (aid,))
    dismissed = storage.one("SELECT count(*) n FROM v2_messages WHERE account_id=? AND state='dismissed'", (aid,))
    return {"ok": True, "total":int(total["n"] if total else 0), "dismissed":int(dismissed["n"] if dismissed else 0), "policy":"Only concrete novel/useful proactive messages; suppress telemetry chatter and repetition."}


@router.get("/desktop/self-assessment")
def self_assessment(authorization: Optional[str] = Header(default=None)):
    a = account(authorization); aid = int(a["id"])
    rel = governance.reliability(aid)
    avg = sum(float(x["consistency_score"]) for x in rel)/len(rel) if rel else 0.5
    return {"ok": True, "profile":a["username"], "functional_self_assessment":{"consistency_calibration":avg,"phenomenal_consciousness_claim":False,"architecture":"7->2->1->1"}}


@router.get("/desktop/hive-budget")
def hive_budget(authorization: Optional[str] = Header(default=None)):
    a = account(authorization)
    return {"ok": True, **governance.cost_status(int(a["id"]))}


@router.get("/desktop/core-research-status")
def core_research_status(authorization: Optional[str] = Header(default=None)):
    a = account(authorization); aid = int(a["id"])
    recent = storage.rows("SELECT id,mode,query,useful,created_at FROM v2_research WHERE account_id=? ORDER BY id DESC LIMIT 30", (aid,))
    return {"ok": True, "profile":a["username"], "recent":recent, "daily_cap":governance.cost_status(aid)["curiosity_daily_search_cap"]}
