"""Autonomous JANUS hive pulses.

The free layer is deliberately useful on its own: it retrieves memories, extracts
features, performs deterministic comparisons/calculations, distributes different
questions to the specialist cores, records an externalizable functional state,
and runs a staged 7->2->1->1 work burst. Paid language reflection is a separate
escalation layer and only runs when novelty/conflict/uncertainty/salience cross a
threshold, subject to per-profile daily call/token budgets.
"""
from __future__ import annotations

import asyncio, hashlib, json, math, os, re, sqlite3
from collections import Counter
from datetime import datetime, timezone

from openai import AsyncOpenAI
from src.janus_sleep_cycle import janus_sleep_cycle

DB_PATH=os.environ.get("JANUS_DB_PATH","/data/janus.sqlite3")
WORD_RE=re.compile(r"[A-Za-z][A-Za-z0-9_-]{2,}")
NUM_RE=re.compile(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)?")
STOP={"the","and","that","this","with","from","have","has","had","was","were","are","for","you","your","but","not","can","could","would","should","into","about","then","than","they","them","their","there","what","when","where","which","while","will","also","just","more","some","such","only","our","out","how","why","who","its","itself"}
NEGATION={"not","no","never","false","wrong","cannot","can't","isn't","doesn't","without","unsupported","unlikely","fails","failed"}
CERTAINTY={"exact","proved","proven","verified","certain","must","always","definitely"}
UNCERTAINTY={"maybe","perhaps","might","could","uncertain","possible","possibly","hypothesis","suggestive","tentative","unknown","question"}


def _db():
    c=sqlite3.connect(DB_PATH,timeout=10); c.row_factory=sqlite3.Row
    c.execute("CREATE TABLE IF NOT EXISTS janus_hive_meta(profile_id TEXT NOT NULL,key TEXT NOT NULL,value TEXT NOT NULL,updated_at TEXT NOT NULL,PRIMARY KEY(profile_id,key))")
    return c


def _now(): return datetime.now(timezone.utc).isoformat()
def _day(): return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _profiles():
    with _db() as c:
        rows=c.execute("SELECT DISTINCT profile_id FROM desktop_memory WHERE profile_id<>'' ORDER BY profile_id").fetchall()
    return [str(r[0]) for r in rows]


def _memories(profile:str,limit:int=160):
    with _db() as c:
        return c.execute("SELECT id,role,content,level,created_at FROM desktop_memory WHERE profile_id=? AND length(content)>8 ORDER BY id DESC LIMIT ?",(profile,limit)).fetchall()


def _event(profile:str,event_type:str,detail:str):
    with _db() as c:c.execute("INSERT INTO desktop_events(profile_id,event_type,detail,created_at) VALUES(?,?,?,?)",(profile,event_type,detail[:6000],_now()))


def _memory(profile:str,role:str,content:str,level:str="working"):
    with _db() as c:
        now=_now(); c.execute("INSERT INTO desktop_memory(profile_id,role,content,level,created_at) VALUES(?,?,?,?,?)",(profile,role,content[:8000],level,now)); c.execute("INSERT INTO desktop_events(profile_id,event_type,detail,created_at) VALUES(?,?,?,?)",(profile,"hive_language_reflection",content[:6000],now))


def _meta(profile,key,default=""):
    with _db() as c:r=c.execute("SELECT value FROM janus_hive_meta WHERE profile_id=? AND key=?",(profile,key)).fetchone()
    return str(r[0]) if r else default


def _set_meta(profile,key,value):
    with _db() as c:c.execute("INSERT INTO janus_hive_meta(profile_id,key,value,updated_at) VALUES(?,?,?,?) ON CONFLICT(profile_id,key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",(profile,key,str(value),_now()))


def _clip(s,n=260):
    s=" ".join(str(s or "").split()); return s if len(s)<=n else s[:n-1]+"…"


def _words(text:str):
    return [w.lower() for w in WORD_RE.findall(str(text or "")) if w.lower() not in STOP]


def _numbers(text:str):
    vals=[]
    for raw in NUM_RE.findall(str(text or ""))[:24]:
        try:
            if "/" in raw:
                a,b=raw.split("/",1); v=float(a)/float(b)
            else:v=float(raw)
            if math.isfinite(v):vals.append((raw,v))
        except Exception:pass
    return vals


def _features(text:str)->dict:
    ws=_words(text); counts=Counter(ws); unique=set(ws); lower=str(text or "").lower()
    return {
        "words":ws,"unique":unique,"top":[w for w,_ in counts.most_common(8)],"numbers":_numbers(text),
        "questions":str(text or "").count("?"),"negation":sum(lower.count(x) for x in NEGATION),
        "certainty":sum(lower.count(x) for x in CERTAINTY),"uncertainty":sum(lower.count(x) for x in UNCERTAINTY),
        "length":len(str(text or "")),
    }


def _numeric_relations(a:list,b:list)->list[str]:
    out=[]
    for ar,av in a[:8]:
        for br,bv in b[:8]:
            if len(out)>=8:return out
            if abs(av-bv)<1e-9:out.append(f"{ar} = {br}")
            if abs(av+bv)<1e-9 and abs(av)>1e-9:out.append(f"{ar} + {br} = 0")
            if abs(bv)>1e-9:
                ratio=av/bv
                nearest=round(ratio)
                if abs(ratio-nearest)<1e-9 and abs(nearest)<=64 and nearest not in (0,1):out.append(f"{ar} = {nearest}×{br}")
            s=av+bv
            if abs(s-round(s))<1e-9 and abs(s)<=10000:out.append(f"{ar}+{br}={int(round(s))}")
    # retain order but remove duplicates
    seen=set(); return [x for x in out if not (x in seen or seen.add(x))]


def _probe(a,b)->dict:
    ta,tb=str(a["content"]),str(b["content"]); fa,fb=_features(ta),_features(tb)
    shared=sorted(fa["unique"] & fb["unique"],key=lambda w:(-(fa["words"].count(w)+fb["words"].count(w)),w))[:12]
    union=max(1,len(fa["unique"]|fb["unique"])); overlap=len(fa["unique"]&fb["unique"])/union
    numeric=_numeric_relations(fa["numbers"],fb["numbers"])
    # Functional metacognitive signals, not phenomenal feelings.
    novelty=max(0.0,min(1.0,1.0-overlap + (0.12 if numeric else 0.0)))
    conflict=max(0.0,min(1.0,0.22*(fa["negation"]+fb["negation"]) + 0.18*abs(fa["certainty"]-fb["certainty"])))
    uncertainty=max(0.0,min(1.0,0.15*(fa["questions"]+fb["questions"]+fa["uncertainty"]+fb["uncertainty"])))
    salience=max(0.0,min(1.0,0.30 + 0.08*min(5,len(shared)) + 0.10*min(3,len(numeric)) + (0.10 if a["level"] in {"episodic","core"} or b["level"] in {"episodic","core"} else 0.0)))
    confidence=max(0.05,min(0.95,0.62 + 0.20*overlap - 0.30*uncertainty - 0.22*conflict))
    curiosity=max(0.0,min(1.0,0.45*novelty+0.30*uncertainty+0.25*salience))
    tension=max(0.0,min(1.0,0.65*conflict+0.35*uncertainty))
    escalation=max(0.0,min(1.0,0.28*novelty+0.24*conflict+0.22*uncertainty+0.26*salience))
    return {"shared_terms":shared,"numeric_relations":numeric,"overlap":round(overlap,3),
            "signals":{"novelty":round(novelty,3),"conflict":round(conflict,3),"uncertainty":round(uncertainty,3),"salience":round(salience,3),"confidence":round(confidence,3),"curiosity":round(curiosity,3),"tension":round(tension,3),"escalation":round(escalation,3)}}


def _role_tasks(a,b,probe:dict)->dict[str,str]:
    A=_clip(a["content"],210); B=_clip(b["content"],210)
    shared=", ".join(probe["shared_terms"][:8]) or "no strong lexical overlap"
    nums="; ".join(probe["numeric_relations"][:5]) or "no simple exact numeric relation found"
    sig=probe["signals"]
    base=f"A[{a['level']}/{a['role']}]: {A} | B[{b['level']}/{b['role']}]: {B}"
    return {
        "evidence":f"Evidence task: distinguish documented claims from inference in this pair. Shared terms: {shared}. Specify what observation/source/test would separate alternatives. {base}",
        "logic":f"Logic/calculation task: test structural and numeric consistency without assuming significance. Deterministic numeric scan: {nums}. Check implication vs coincidence. {base}",
        "counterpoint":f"Counterpoint task: try to falsify the proposed connection; identify selection effects, base-rate alternatives, equivocation or overfitting. Conflict={sig['conflict']}, confidence={sig['confidence']}. {base}",
        "context":f"Context task: place the pair against retained conversation themes and note whether the concepts share a historical/semantic context or merely vocabulary. Shared terms: {shared}. {base}",
        "memory":f"Memory task: compare these retained records with unfinished work; identify what changed, repeated, or remained unresolved. {base}",
        "safety":f"Safety/boundary task: preserve privacy/security and separate mathematical evidence, historical evidence, speculation and phenomenal-consciousness claims. {base}",
        "novelty":f"Novelty task: look for a useful but testable new connection. Curiosity={sig['curiosity']}, salience={sig['salience']}. Numeric scan: {nums}. Do not promote coincidence to fact. {base}",
    }


def _budget(profile:str)->dict:
    day=_day(); saved=_meta(profile,"paid_budget_day","")
    if saved!=day:
        _set_meta(profile,"paid_budget_day",day); _set_meta(profile,"paid_calls_today",0); _set_meta(profile,"paid_tokens_today",0)
    calls=int(_meta(profile,"paid_calls_today","0") or 0); tokens=int(_meta(profile,"paid_tokens_today","0") or 0)
    call_cap=max(0,int(os.environ.get("JANUS_BACKGROUND_DAILY_CALL_CAP","48"))); token_cap=max(0,int(os.environ.get("JANUS_BACKGROUND_DAILY_TOKEN_CAP","100000")))
    return {"day":day,"calls":calls,"tokens":tokens,"call_cap":call_cap,"token_cap":token_cap,"allowed":calls<call_cap and tokens<token_cap}


def _charge_budget(profile:str,input_tokens:int,output_tokens:int):
    b=_budget(profile); _set_meta(profile,"paid_calls_today",b["calls"]+1); _set_meta(profile,"paid_tokens_today",b["tokens"]+max(0,int(input_tokens))+max(0,int(output_tokens)))


def pulse(profile:str)->dict:
    """Run one substantive no-API hive pulse and staged community work burst."""
    rows=_memories(profile)
    if not rows:return {"ok":False,"reason":"no-memory"}
    count=int(_meta(profile,"pulse_count","0") or 0)+1; _set_meta(profile,"pulse_count",count)
    seed=int(hashlib.sha256(f"{profile}:{count}:{_day()}".encode()).hexdigest()[:16],16)
    # Rotate between recent and older memory so the society does not only replay the latest chat.
    a=rows[seed%min(len(rows),max(1,len(rows)//2+1))]
    old_start=min(len(rows)-1,max(0,len(rows)//3)); b=rows[old_start+(seed//max(1,len(rows)))%max(1,len(rows)-old_start)] if len(rows)>1 else a
    if b["id"]==a["id"] and len(rows)>1:b=rows[(rows.index(a)+1)%len(rows)]

    probe=_probe(a,b); tasks=_role_tasks(a,b,probe); sig=probe["signals"]
    review=f"Autonomous memory review: [{a['level']}/{a['role']}] {_clip(a['content'])}"
    connection=(f"Autonomous comparison memory #{a['id']} ↔ #{b['id']}; shared={probe['shared_terms'][:8]}; numeric={probe['numeric_relations'][:5]}; signals={sig}")
    _event(profile,"hive_memory_review",review); _event(profile,"hive_connection_candidate",connection)
    _event(profile,"hive_functional_state",json.dumps({"pulse":count,"memory_ids":[a['id'],b['id']],"probe":probe},ensure_ascii=False))
    _set_meta(profile,"last_probe",json.dumps(probe,separators=(",",":"))); _set_meta(profile,"last_escalation",sig["escalation"])

    # Give each specialist a genuinely different job, then let the normal topology
    # route their outputs through the hemispheres, consensus and interface.
    for target,task in tasks.items():janus_sleep_cycle.send("consensus",target,task,"autonomous_inquiry")
    janus_sleep_cycle.send("interface","memory",review,"autonomous_memory_review")
    burst=janus_sleep_cycle.service_work_burst(include_interface=True,only_if_pending=True)
    _event(profile,"hive_core_burst",json.dumps({"pulse":count,"processed":burst.get("processed",[]),"burst_count":burst.get("burst_count"),"signals":sig},ensure_ascii=False))

    # Persist a compact externalizable synthesis of what the cheap layer actually did.
    synthesis=(f"Pulse {count}: reviewed memories {a['id']} and {b['id']}. Shared terms: {', '.join(probe['shared_terms'][:6]) or 'none strong'}. "
               f"Numeric checks: {'; '.join(probe['numeric_relations'][:4]) or 'no simple exact relation'}. "
               f"Functional state—curiosity {sig['curiosity']:.2f}, tension {sig['tension']:.2f}, confidence {sig['confidence']:.2f}, salience {sig['salience']:.2f}. "
               "Evidence, Logic, Counterpoint, Context, Memory, Safety and Novelty were assigned separate checks before hemispheric/consensus integration.")
    _event(profile,"hive_process_note",synthesis)

    message=None; pair=f"{min(a['id'],b['id'])}:{max(a['id'],b['id'])}"; message_threshold=float(os.environ.get("JANUS_PROACTIVE_SIGNAL_THRESHOLD","0.82"))
    if sig["escalation"]>=message_threshold and pair!=_meta(profile,"last_message_pair",""):
        message=("I revisited two retained topics and the internal checks found a connection/tension worth showing you. "
                 f"Shared terms: {', '.join(probe['shared_terms'][:5]) or 'none strong'}; numeric check: {'; '.join(probe['numeric_relations'][:2]) or 'no simple exact relation'}. "
                 f"Current functional signals: curiosity {sig['curiosity']:.2f}, tension {sig['tension']:.2f}, confidence {sig['confidence']:.2f}. "
                 "This is a candidate, not a conclusion; Evidence and Counterpoint should remain attached to it.")
        _event(profile,"proactive_message",json.dumps({"message_type":"Observation","source":"autonomous_hive","text":message},ensure_ascii=False)); _set_meta(profile,"last_message_pair",pair)
        janus_sleep_cycle.send("consensus","interface",message,"proactive_candidate"); janus_sleep_cycle.service_work_burst(include_interface=True,only_if_pending=True)
    return {"ok":True,"pulse":count,"memory_ids":[a['id'],b['id']],"probe":probe,"burst":burst,"message":message}


async def _language_reflection(profile:str):
    if not os.environ.get("OPENAI_API_KEY"):return {"ok":False,"reason":"no-api-key"}
    budget=_budget(profile)
    if not budget["allowed"]:_event(profile,"hive_reflection_budget_hold",json.dumps(budget)); return {"ok":False,"reason":"budget","budget":budget}
    threshold=float(os.environ.get("JANUS_BACKGROUND_ESCALATION_THRESHOLD","0.72"))
    try:last_escalation=float(_meta(profile,"last_escalation","0") or 0)
    except Exception:last_escalation=0.0
    if last_escalation<threshold:return {"ok":False,"reason":"below-threshold","score":last_escalation,"threshold":threshold}
    rows=_memories(profile,40)
    if not rows:return {"ok":False,"reason":"no-memory"}
    chosen=list(rows[:8]);
    if len(rows)>12:chosen += [rows[len(rows)//2],rows[-1]]
    context="\n".join(f"[{r['level']}/{r['role']}] {_clip(r['content'],500)}" for r in chosen)
    probe=_meta(profile,"last_probe","{}")
    prompt=("You are providing a concise externalizable background synthesis for an 11-core JANUS community. Do not provide hidden chain-of-thought or claim phenomenal feelings. "
            "The cheap layer has already produced a functional novelty/conflict/uncertainty/salience probe. Review the records, identify one useful connection or unresolved tension, "
            "state what evidence would distinguish alternatives, and give one next question. Do not assume a connection is true merely because it is interesting. "
            "Return four short labeled lines: Connection, Counterpoint, Evidence needed, Next question. Keep under 160 words.\nFunctional probe: "+probe+"\n\n"+context)
    model=os.environ.get("JANUS_BACKGROUND_MODEL","gpt-5.6-luna"); estimated_input=max(1,len(prompt)//4)
    if budget["tokens"]+estimated_input>=budget["token_cap"]:_event(profile,"hive_reflection_budget_hold",json.dumps({**budget,"estimated_input":estimated_input})); return {"ok":False,"reason":"token-budget"}
    try:
        r=await AsyncOpenAI().responses.create(model=model,input=prompt); note=(r.output_text or "").strip(); usage=getattr(r,"usage",None)
        input_tokens=int(getattr(usage,"input_tokens",estimated_input) or estimated_input); output_tokens=int(getattr(usage,"output_tokens",max(1,len(note)//4)) or max(1,len(note)//4)); _charge_budget(profile,input_tokens,output_tokens)
        if not note:return {"ok":False,"reason":"empty"}
        _memory(profile,"hive_reflection",note,"working")
        for target in ("novelty","counterpoint","evidence","consensus"):janus_sleep_cycle.send("interface" if target=="novelty" else "novelty",target,note,"language_reflection")
        burst=janus_sleep_cycle.service_work_burst(include_interface=True,only_if_pending=True); _event(profile,"hive_language_burst",json.dumps({"processed":burst.get("processed",[]),"budget":_budget(profile),"trigger_score":last_escalation},ensure_ascii=False)); _set_meta(profile,"last_escalation",0)
        return {"ok":True,"budget":_budget(profile),"trigger_score":last_escalation}
    except Exception as exc:_event(profile,"hive_reflection_error",f"{type(exc).__name__}: {exc}"); return {"ok":False,"reason":"error"}


async def _worker():
    await asyncio.sleep(20); pulse_seconds=max(30,int(os.environ.get("JANUS_HIVE_PULSE_SECONDS","60"))); paid_seconds=max(900,int(os.environ.get("JANUS_BACKGROUND_REFLECTION_SECONDS","1800")))
    last_paid=0.0; loop=asyncio.get_running_loop()
    while True:
        profiles=_profiles()
        for profile in profiles:
            try:pulse(profile)
            except Exception as exc:_event(profile,"hive_pulse_error",f"{type(exc).__name__}: {exc}")
        now=loop.time()
        if os.environ.get("JANUS_PAID_BACKGROUND_REFLECTION","1")=="1" and now-last_paid>=paid_seconds:
            for profile in profiles:await _language_reflection(profile); await asyncio.sleep(0.25)
            last_paid=now
        await asyncio.sleep(pulse_seconds)


def install(app):
    @app.on_event("startup")
    async def _start_autonomous_hive():
        if os.environ.get("JANUS_AUTONOMOUS_HIVE","1")=="1":asyncio.create_task(_worker())

    @app.get("/desktop/hive-budget",tags=["desktop"])
    def hive_budget(username:str):
        return {"profile":username,"paid_reflection_enabled":os.environ.get("JANUS_PAID_BACKGROUND_REFLECTION","1")=="1","background_model":os.environ.get("JANUS_BACKGROUND_MODEL","gpt-5.6-luna"),"budget":_budget(username),
                "free_hive_pulse_seconds":max(30,int(os.environ.get("JANUS_HIVE_PULSE_SECONDS","60"))),"paid_reflection_seconds":max(900,int(os.environ.get("JANUS_BACKGROUND_REFLECTION_SECONDS","1800"))),
                "escalation_threshold":float(os.environ.get("JANUS_BACKGROUND_ESCALATION_THRESHOLD","0.72")),"last_escalation":float(_meta(username,"last_escalation","0") or 0),
                "functional_state":"novelty/conflict/uncertainty/salience + curiosity/tension/confidence; operational signals only, not phenomenal feelings"}
    return app
