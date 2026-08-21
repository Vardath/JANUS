"""JANUS self-assessment and disagreement-resolution loop.

Periodically inspects the 11-core society's externalizable state, measures where
specialist/hemisphere outputs disagree, assigns targeted follow-up work, and now
services that work immediately through a staged community burst. Records concise
assessment summaries only; it does not expose hidden model chain-of-thought.
"""
from __future__ import annotations

import asyncio, json, os, sqlite3
from datetime import datetime, timezone

from src.janus_sleep_cycle import janus_sleep_cycle

DB_PATH=os.environ.get("JANUS_DB_PATH","/data/janus.sqlite3")


def _now(): return datetime.now(timezone.utc).isoformat()

def _db():
    c=sqlite3.connect(DB_PATH,timeout=10); c.row_factory=sqlite3.Row
    c.execute("""CREATE TABLE IF NOT EXISTS janus_self_assessment(
        id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,
        disagreement_score REAL NOT NULL,unresolved_json TEXT NOT NULL,
        action_summary TEXT NOT NULL)""")
    return c

def _tokens(text:str)->set[str]:
    out=set()
    for raw in str(text or "").lower().replace("/"," ").replace("_"," ").split():
        w="".join(ch for ch in raw if ch.isalnum())
        if len(w)>=4:out.add(w)
    return out

def _distance(a:str,b:str)->float:
    A,B=_tokens(a),_tokens(b)
    if not A and not B:return 0.0
    if not A or not B:return 1.0
    return 1.0-(len(A&B)/max(1,len(A|B)))

def assess_once()->dict:
    st=janus_sleep_cycle.status(); cores=st.get("cores") or {}
    pairs=[("evidence","counterpoint"),("logic","novelty"),("context","safety"),("left_hemisphere","right_hemisphere"),("consensus","interface")]
    unresolved=[]; scores=[]
    for a,b in pairs:
        ta=str((cores.get(a) or {}).get("last_output") or ""); tb=str((cores.get(b) or {}).get("last_output") or "")
        if not ta and not tb:continue
        d=_distance(ta,tb); scores.append(d)
        if d>=0.72:
            unresolved.append({"a":a,"b":b,"score":round(d,3)})
            issue=(f"Self-assessment found unresolved divergence between {a} and {b} (distance {d:.2f}). "
                   "Re-evaluate the same issue, state what evidence or assumption would resolve the difference, and do not force agreement without support.")
            for target in {a,b,"evidence","logic","counterpoint"}:
                janus_sleep_cycle.send("consensus",target,issue,"self_assessment_check")
    score=sum(scores)/len(scores) if scores else 0.0
    if unresolved:
        summary=(f"Self-assessment: {len(unresolved)} unresolved disagreement pair(s), mean divergence {score:.2f}. "
                 "Assigned follow-up checks; consensus should update only after the conflict narrows or new evidence appears.")
    else:
        summary=(f"Self-assessment: no major unresolved divergence detected; mean divergence {score:.2f}. "
                 "Consensus remains provisional and should continue checking for contradictory evidence.")
    janus_sleep_cycle.send("consensus","interface",summary,"self_assessment_summary")
    burst=janus_sleep_cycle.service_work_burst(include_interface=True,only_if_pending=True)
    with _db() as c:
        c.execute("INSERT INTO janus_self_assessment(created_at,disagreement_score,unresolved_json,action_summary) VALUES(?,?,?,?)",(_now(),score,json.dumps(unresolved),summary))
        try:
            profiles=[str(r[0]) for r in c.execute("SELECT DISTINCT profile_id FROM desktop_memory WHERE profile_id<>''")]
            for p in profiles:c.execute("INSERT INTO desktop_events(profile_id,event_type,detail,created_at) VALUES(?,?,?,?)",(p,"self_assessment",summary,_now()))
        except Exception:pass
    return {"score":score,"unresolved":unresolved,"summary":summary,"burst":burst}

async def _worker():
    await asyncio.sleep(45); interval=max(60,int(os.environ.get("JANUS_SELF_ASSESS_SECONDS","300")))
    while True:
        try:assess_once()
        except Exception:pass
        await asyncio.sleep(interval)

def install(app):
    @app.on_event("startup")
    async def _start_self_assessment():
        if os.environ.get("JANUS_SELF_ASSESS","1")=="1":asyncio.create_task(_worker())

    @app.get("/desktop/self-assessment",tags=["desktop"])
    def self_assessment_status(limit:int=20):
        with _db() as c:rows=c.execute("SELECT id,created_at,disagreement_score,unresolved_json,action_summary FROM janus_self_assessment ORDER BY id DESC LIMIT ?",(max(1,min(limit,100)),)).fetchall()
        items=[]
        for r in rows:
            x=dict(r)
            try:x["unresolved"]=json.loads(x.pop("unresolved_json"))
            except Exception:x["unresolved"]=[]
            items.append(x)
        return {"enabled":os.environ.get("JANUS_SELF_ASSESS","1")=="1","interval_seconds":max(60,int(os.environ.get("JANUS_SELF_ASSESS_SECONDS","300"))),"items":items}
    return app
