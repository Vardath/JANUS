"""Phase 2 Step 4: deterministic background usefulness audit and gate.

Measures whether autonomous curiosity/research is producing concrete, novel subject
matter rather than repetitive JANUS/process self-reference. The gate is zero-API and
runs before a background web/model search is scheduled, so rejected candidates do
not spend external budget. Explicit foreground user requests are not affected.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from fastapi import APIRouter, Header

import auth

DB_PATH = Path(os.getenv("JANUS_DB_PATH", "/data/janus.sqlite3"))
MIN_SCORE = max(0.0, min(1.0, float(os.getenv("JANUS_BACKGROUND_USEFULNESS_MIN_SCORE", "0.48"))))
REPETITION_BLOCK = max(0.4, min(0.98, float(os.getenv("JANUS_BACKGROUND_REPETITION_BLOCK", "0.74"))))
REPETITION_WARN = max(0.2, min(REPETITION_BLOCK, float(os.getenv("JANUS_BACKGROUND_REPETITION_WARN", "0.56"))))
PROCESS_RATIO_BLOCK = max(0.08, min(0.8, float(os.getenv("JANUS_BACKGROUND_PROCESS_RATIO_BLOCK", "0.24"))))

router = APIRouter(prefix="/background-usefulness", tags=["background-usefulness"])
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9_-]{2,}")
_PROCESS = {
    "janus","core","cores","cycle","cycles","routing","interface","consensus","hemisphere","hemispheres",
    "telemetry","fano","projection","runtime","pipeline","processing","process","specialist","specialists",
    "counter","counters","phase","heartbeat","maintenance","integration","integrating","grounding",
}
_CONCRETE = {
    "study","paper","source","sources","measurement","measure","observed","observation","experiment",
    "test","prediction","result","results","data","dataset","comparison","mechanism","evidence","historical",
    "archaeological","ecology","engineering","mathematical","physics","astronomy","geology","linguistic",
    "distributed","memory","error","recovery","animal","behaviour","cognitive","system","systems",
}
_SELF_REFERENTIAL = (
    "what are the cores thinking", "how janus is processing", "janus cycle", "janus cores", "consensus and interface",
    "fano direction", "current telemetry", "runtime counters", "background processing status",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("""CREATE TABLE IF NOT EXISTS janus_background_usefulness(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        profile_id TEXT NOT NULL,
        event_kind TEXT NOT NULL,
        source_id INTEGER,
        core_name TEXT NOT NULL DEFAULT '',
        mode TEXT NOT NULL DEFAULT '',
        topic TEXT NOT NULL DEFAULT '',
        score REAL NOT NULL,
        novelty REAL NOT NULL,
        process_ratio REAL NOT NULL,
        max_similarity REAL NOT NULL,
        decision TEXT NOT NULL,
        reasons_json TEXT NOT NULL DEFAULT '[]',
        created_at TEXT NOT NULL
    )""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_background_usefulness_profile_time ON janus_background_usefulness(profile_id,created_at DESC)")
    return c


def _normalize_word(word: str) -> str:
    """Small deterministic morphology normalizer for repetition detection.

    This intentionally is not a language model or full stemmer. It only removes a
    few common English inflections so near-identical background queries such as
    node/nodes and fail/failures cannot evade the duplicate gate through wording.
    """
    w = word.lower()
    irregular = {"failures": "fail", "failure": "fail", "nodes": "node"}
    if w in irregular:
        return irregular[w]
    if len(w) > 5 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 5 and w.endswith("ing"):
        return w[:-3]
    if len(w) > 4 and w.endswith("ed"):
        return w[:-2]
    if len(w) > 4 and w.endswith("es"):
        return w[:-2]
    if len(w) > 3 and w.endswith("s"):
        return w[:-1]
    return w


def _tokens(text: str) -> set[str]:
    return {_normalize_word(w) for w in _WORD.findall(str(text or ""))}


def similarity(a: str, b: str) -> float:
    x, y = _tokens(a), _tokens(b)
    if not x or not y:
        return 0.0
    # Jaccard keeps broad topic overlap from looking identical. A containment term
    # catches short reformulations of the same query. Use the stronger signal.
    jaccard = len(x & y) / max(1, len(x | y))
    containment = len(x & y) / max(1, min(len(x), len(y)))
    return max(jaccard, containment)


def recent_queries(profile: str, limit: int = 24) -> list[str]:
    try:
        with _db() as c:
            rows = c.execute(
                "SELECT query FROM janus_curiosity_searches WHERE profile_id=? AND status IN ('pending','complete') ORDER BY id DESC LIMIT ?",
                (profile, max(1, min(int(limit), 100))),
            ).fetchall()
        return [str(r[0] or "") for r in rows]
    except Exception:
        return []


def assess_text(text: str, recent_texts: Iterable[str] = ()) -> dict[str, Any]:
    clean = " ".join(str(text or "").split()).strip()
    words = _tokens(clean)
    if not clean:
        return {"pass": False, "score": 0.0, "novelty": 0.0, "process_ratio": 0.0, "max_similarity": 0.0, "reasons": ["empty"]}

    process_ratio = len(words & _PROCESS) / max(1, len(words))
    concrete = len(words & _CONCRETE)
    lower = clean.lower()
    self_ref_hits = sum(1 for phrase in _SELF_REFERENTIAL if phrase in lower)
    max_sim = max((similarity(clean, old) for old in recent_texts if str(old or "").strip()), default=0.0)
    novelty = max(0.0, 1.0 - max_sim)

    score = 0.34
    reasons: list[str] = []
    if 35 <= len(clean) <= 1200:
        score += 0.10
    elif len(clean) < 20:
        score -= 0.20; reasons.append("too-thin")
    if concrete >= 2:
        score += min(0.24, 0.05 * concrete)
    elif concrete == 0:
        score -= 0.10; reasons.append("low-concrete-subject-matter")
    if "?" in clean or any(x in lower for x in ("find ", "compare ", "test ", "verify ", "measure ", "what distinguishes", "what evidence")):
        score += 0.08
    if self_ref_hits:
        score -= min(0.45, 0.22 * self_ref_hits); reasons.append("self-referential-loop")
    if process_ratio >= PROCESS_RATIO_BLOCK:
        score -= 0.35; reasons.append("process-heavy")
    elif process_ratio >= PROCESS_RATIO_BLOCK * 0.65:
        score -= 0.12; reasons.append("process-leaning")
    if max_sim >= REPETITION_BLOCK:
        score -= 0.42; reasons.append("near-duplicate")
    elif max_sim >= REPETITION_WARN:
        score -= 0.18; reasons.append("repetitive")
    else:
        score += min(0.12, 0.12 * novelty)

    score = max(0.0, min(1.0, score))
    passed = score >= MIN_SCORE and max_sim < REPETITION_BLOCK and process_ratio < PROCESS_RATIO_BLOCK and not self_ref_hits
    if passed:
        reasons.append("usefulness-threshold-met")
    return {
        "pass": passed,
        "score": round(score, 3),
        "novelty": round(novelty, 3),
        "process_ratio": round(process_ratio, 3),
        "max_similarity": round(max_sim, 3),
        "concrete_terms": concrete,
        "reasons": reasons,
    }


def _record(profile: str, event_kind: str, assessment: dict[str, Any], *, source_id: int | None = None,
            core: str = "", mode: str = "", topic: str = "") -> None:
    try:
        with _db() as c:
            c.execute(
                """INSERT INTO janus_background_usefulness
                (profile_id,event_kind,source_id,core_name,mode,topic,score,novelty,process_ratio,max_similarity,decision,reasons_json,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (profile,event_kind,source_id,core,mode,topic[:3000],float(assessment.get("score",0)),float(assessment.get("novelty",0)),
                 float(assessment.get("process_ratio",0)),float(assessment.get("max_similarity",0)),
                 "accept" if assessment.get("pass") else "suppress",json.dumps(assessment.get("reasons",[]),separators=(",",":")),_now()),
            )
    except Exception:
        pass


def gate_candidate(profile: str, core: str, mode: str, query: str, rationale: str = "") -> dict[str, Any]:
    recent = recent_queries(profile)
    assessment = assess_text(" ".join(x for x in (query, rationale) if x), recent)

    # Similarity must be judged on the actual proposed query as well as the combined
    # query+rationale. Otherwise an appended rationale can dilute an exact duplicate.
    query_sim = max((similarity(query, old) for old in recent if str(old or "").strip()), default=0.0)
    if query_sim > float(assessment.get("max_similarity", 0.0)):
        assessment["max_similarity"] = round(query_sim, 3)
        assessment["novelty"] = round(max(0.0, 1.0 - query_sim), 3)
        if query_sim >= REPETITION_BLOCK:
            assessment["pass"] = False
            if "near-duplicate" not in assessment["reasons"]:
                assessment["reasons"].append("near-duplicate")
        elif query_sim >= REPETITION_WARN and "repetitive" not in assessment["reasons"]:
            assessment["reasons"].append("repetitive")

    _record(profile, "candidate", assessment, core=core, mode=mode, topic=query)
    return assessment


def audit(profile: str, limit: int = 40) -> dict[str, Any]:
    limit=max(1,min(int(limit or 40),100))
    searches=[]
    try:
        with _db() as c:
            rows=c.execute(
                "SELECT id,core_name,mode,query,result,sources_json,status FROM janus_curiosity_searches WHERE profile_id=? ORDER BY id DESC LIMIT ?",
                (profile,limit),
            ).fetchall()
        searches=[dict(r) for r in reversed(rows)]
    except Exception:
        searches=[]

    prior_results: list[str]=[]
    scored=[]
    for row in searches:
        if row.get("status") != "complete" or not str(row.get("result") or "").strip():
            continue
        a=assess_text(str(row.get("result") or ""), prior_results[-16:])
        try:
            sources=json.loads(str(row.get("sources_json") or "[]"))
        except Exception:
            sources=[]
        if sources:
            a["score"]=round(min(1.0,float(a["score"])+0.10),3)
            if a["score"] >= MIN_SCORE and a["max_similarity"] < REPETITION_BLOCK and a["process_ratio"] < PROCESS_RATIO_BLOCK:
                a["pass"]=True
        scored.append({"id":int(row["id"]),"core":row.get("core_name"),"mode":row.get("mode"),"query":row.get("query"),**a,"source_count":len(sources)})
        prior_results.append(str(row.get("result") or ""))

    useful=sum(1 for x in scored if x["pass"])
    repetitive=sum(1 for x in scored if x["max_similarity"] >= REPETITION_WARN)
    process_heavy=sum(1 for x in scored if x["process_ratio"] >= PROCESS_RATIO_BLOCK)
    avg_score=round(sum(float(x["score"]) for x in scored)/len(scored),3) if scored else 0.0
    usefulness_rate=round(useful/len(scored),3) if scored else 0.0

    try:
        with _db() as c:
            recent_gate=[dict(r) for r in c.execute(
                "SELECT id,event_kind,core_name,mode,topic,score,novelty,process_ratio,max_similarity,decision,reasons_json,created_at FROM janus_background_usefulness WHERE profile_id=? ORDER BY id DESC LIMIT 30",
                (profile,),
            ).fetchall()]
    except Exception:
        recent_gate=[]
    for r in recent_gate:
        try: r["reasons"]=json.loads(r.pop("reasons_json") or "[]")
        except Exception: r["reasons"]=[]

    return {
        "profile": profile,
        "policy": {"min_score":MIN_SCORE,"repetition_warn":REPETITION_WARN,"repetition_block":REPETITION_BLOCK,"process_ratio_block":PROCESS_RATIO_BLOCK},
        "completed_scored":len(scored),
        "useful":useful,
        "usefulness_rate":usefulness_rate,
        "average_score":avg_score,
        "repetitive":repetitive,
        "process_heavy":process_heavy,
        "recent_results":scored[-12:],
        "recent_gate_decisions":recent_gate,
    }


def install(curiosity_module) -> None:
    if getattr(curiosity_module, "_janus_background_usefulness_installed", False):
        return
    original=getattr(curiosity_module, "_choose_search", None)
    if not callable(original):
        raise RuntimeError("curiosity _choose_search missing")

    def useful_choose_search(profile: str):
        choice=original(profile)
        if not choice:
            return None
        core, mode, query, rationale=choice
        decision=gate_candidate(profile, str(core), str(mode), str(query), str(rationale))
        if not decision.get("pass"):
            return None
        return choice

    curiosity_module._choose_search=useful_choose_search
    curiosity_module._janus_background_usefulness_original_choose_search=original
    curiosity_module._janus_background_usefulness_installed=True


@router.get("/status")
def usefulness_status(limit: int = 40, authorization: str | None = Header(default=None)):
    account=auth.require_account(authorization)
    return {"ok": True, **audit(str(account["username"]), limit)}
