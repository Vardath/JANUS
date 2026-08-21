"""JANUS self-assessment, disagreement resolution, and epistemic regulation.

The loop inspects the externalizable 11-core state and can temporarily rebalance
work when integration/critique is outrunning fresh evidence. This is functional
control telemetry, not hidden chain-of-thought or a consciousness claim.
"""
from __future__ import annotations

import asyncio, json, os, sqlite3, time
from datetime import datetime, timezone

from src.janus_sleep_cycle import janus_sleep_cycle

DB_PATH=os.environ.get("JANUS_DB_PATH","/data/janus.sqlite3")
REGULATION_SECONDS=max(120,int(os.environ.get("JANUS_EPISTEMIC_REGULATION_SECONDS","900")))
IMBALANCE_THRESHOLD=float(os.environ.get("JANUS_EPISTEMIC_IMBALANCE_THRESHOLD","1.65"))
SELF_REFERENCE_THRESHOLD=float(os.environ.get("JANUS_EPISTEMIC_SELF_REFERENCE_THRESHOLD","0.45"))


def _now(): return datetime.now(timezone.utc).isoformat()

def _db():
    c=sqlite3.connect(DB_PATH,timeout=10); c.row_factory=sqlite3.Row
    c.execute("""CREATE TABLE IF NOT EXISTS janus_self_assessment(
        id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,
        disagreement_score REAL NOT NULL,unresolved_json TEXT NOT NULL,
        action_summary TEXT NOT NULL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS janus_epistemic_regulation(
        profile_id TEXT PRIMARY KEY, active INTEGER NOT NULL DEFAULT 0,
        reason TEXT NOT NULL DEFAULT '', activated_at TEXT, expires_at REAL NOT NULL DEFAULT 0,
        imbalance REAL NOT NULL DEFAULT 0, self_reference REAL NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL)""")
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

def _profiles(c)->list[str]:
    try:return [str(r[0]) for r in c.execute("SELECT DISTINCT profile_id FROM desktop_memory WHERE profile_id<>''")]
    except Exception:return []

def _cycle_metrics(cores:dict)->dict:
    def cyc(n): return int((cores.get(n) or {}).get("cycle_count") or 0)
    grounding=[cyc("evidence"),cyc("logic"),cyc("memory"),cyc("novelty")]
    integration=[cyc("counterpoint"),cyc("consensus"),cyc("interface")]
    g=sum(grounding)/max(1,len(grounding)); i=sum(integration)/max(1,len(integration))
    imbalance=i/max(1.0,g)
    texts=" ".join(str((cores.get(n) or {}).get("last_output") or "").lower() for n in cores)
    markers=("feedback-only","global feedback","self-assessment","consensus","interface","summary")
    hits=sum(texts.count(m) for m in markers)
    words=max(1,len(texts.split()))
    self_reference=min(1.0,(hits*6.0)/words)
    return {"grounding_mean":round(g,2),"integration_mean":round(i,2),"imbalance":round(imbalance,3),"self_reference":round(self_reference,3)}

def _filter_recursive_feedback()->int:
    """Remove stale feedback-only/self-assessment chatter from queues during correction."""
    removed=0
    try:
        lock=getattr(janus_sleep_cycle,"_lock",None)
        if lock: lock.acquire()
        for name,state in janus_sleep_cycle.cores.items():
            if name not in {"counterpoint","left_hemisphere","right_hemisphere","consensus","interface"}:continue
            keep=[]
            for msg in state.inbox:
                text=str(getattr(msg,"content","") or "").lower(); kind=str(getattr(msg,"kind","") or "").lower()
                if "feedback-only" in text or "global feedback" in text or kind in {"feedback","interface_feedback","self_assessment_summary"}:
                    removed+=1; continue
                keep.append(msg)
            state.inbox=keep[-128:]
    except Exception:pass
    finally:
        try:
            if lock: lock.release()
        except Exception:pass
    return removed

def _activate_regulation(profile:str,metrics:dict,reason:str)->None:
    expires=time.time()+REGULATION_SECONDS; stamp=_now()
    with _db() as c:
        c.execute("""INSERT INTO janus_epistemic_regulation(profile_id,active,reason,activated_at,expires_at,imbalance,self_reference,updated_at)
        VALUES(?,1,?,?,?,?,?,?) ON CONFLICT(profile_id) DO UPDATE SET active=1,reason=excluded.reason,activated_at=excluded.activated_at,
        expires_at=excluded.expires_at,imbalance=excluded.imbalance,self_reference=excluded.self_reference,updated_at=excluded.updated_at""",
        (profile,reason,stamp,expires,float(metrics["imbalance"]),float(metrics["self_reference"]),stamp))
        try:c.execute("INSERT INTO desktop_events(profile_id,event_type,detail,created_at) VALUES(?,?,?,?)",(profile,"epistemic_regulation_started",reason,stamp))
        except Exception:pass

def _deactivate_if_expired(profile:str)->None:
    with _db() as c:
        row=c.execute("SELECT active,expires_at FROM janus_epistemic_regulation WHERE profile_id=?",(profile,)).fetchone()
        if row and int(row["active"] or 0)==1 and float(row["expires_at"] or 0)<=time.time():
            c.execute("UPDATE janus_epistemic_regulation SET active=0,updated_at=? WHERE profile_id=?",(_now(),profile))
            try:c.execute("INSERT INTO desktop_events(profile_id,event_type,detail,created_at) VALUES(?,?,?,?)",(profile,"epistemic_regulation_ended","Temporary grounding correction expired; normal weighting resumed.",_now()))
            except Exception:pass

def _grounding_burst(reason:str)->dict:
    removed=_filter_recursive_feedback()
    task=("Epistemic correction: integration is outrunning fresh grounding. Identify one concrete unresolved claim from current retained work; "
          "seek a falsifiable observation, missing fact, counterexample, or external source that could change the conclusion. Do not summarize prior summaries. "
          f"Trigger: {reason}")
    janus_sleep_cycle.send("consensus","evidence",task,"epistemic_grounding")
    janus_sleep_cycle.send("consensus","logic",task,"epistemic_grounding")
    janus_sleep_cycle.send("consensus","memory","Find the most relevant unfinished user-directed question or unresolved claim; avoid generic telemetry.","epistemic_grounding")
    janus_sleep_cycle.send("consensus","novelty","Generate one new, testable avenue that would require fresh evidence rather than recursive synthesis.","epistemic_grounding")
    janus_sleep_cycle.send("consensus","safety","Keep claim boundaries intact while fresh evidence is sought.","epistemic_grounding")
    burst=janus_sleep_cycle.service_work_burst(include_interface=True,only_if_pending=True)
    return {"removed_recursive_messages":removed,"burst":burst}

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
                   "State what new evidence or assumption would resolve it; do not force agreement without support.")
            for target in {a,b,"evidence","logic","counterpoint"}:janus_sleep_cycle.send("consensus",target,issue,"self_assessment_check")
    score=sum(scores)/len(scores) if scores else 0.0
    metrics=_cycle_metrics(cores)
    low_productivity=(metrics["imbalance"]>=IMBALANCE_THRESHOLD or metrics["self_reference"]>=SELF_REFERENCE_THRESHOLD)
    reason=(f"Integration/grounding ratio {metrics['imbalance']:.2f}; self-reference signal {metrics['self_reference']:.2f}. "
            "Temporarily prioritize Evidence, Logic, Memory and Novelty; suppress recursive feedback and request fresh grounding.")
    correction=None
    if low_productivity:
        correction=_grounding_burst(reason)
    if unresolved:
        summary=(f"Self-assessment: {len(unresolved)} unresolved disagreement pair(s), mean divergence {score:.2f}. ")
    else:
        summary=(f"Self-assessment: no major unresolved divergence detected; mean divergence {score:.2f}. ")
    if low_productivity:
        summary+=("Epistemic productivity is low, so JANUS activated temporary grounding regulation instead of merely recommending it. "
                  f"{reason}")
    else:
        summary+=("Grounding/integration balance is acceptable; normal weighting remains active.")
    janus_sleep_cycle.send("consensus","interface",summary,"self_assessment_summary")
    burst=janus_sleep_cycle.service_work_burst(include_interface=True,only_if_pending=True)
    with _db() as c:
        c.execute("INSERT INTO janus_self_assessment(created_at,disagreement_score,unresolved_json,action_summary) VALUES(?,?,?,?)",(_now(),score,json.dumps(unresolved),summary))
        profiles=_profiles(c)
        for p in profiles:
            if low_productivity:_activate_regulation(p,metrics,reason)
            else:_deactivate_if_expired(p)
            try:c.execute("INSERT INTO desktop_events(profile_id,event_type,detail,created_at) VALUES(?,?,?,?)",(p,"self_assessment",summary,_now()))
            except Exception:pass
    return {"score":score,"unresolved":unresolved,"metrics":metrics,"regulation_active":low_productivity,"correction":correction,"summary":summary,"burst":burst}

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
        return {"enabled":os.environ.get("JANUS_SELF_ASSESS","1")=="1","interval_seconds":max(60,int(os.environ.get("JANUS_SELF_ASSESS_SECONDS","300"))),"regulation_seconds":REGULATION_SECONDS,"items":items}
    return app
