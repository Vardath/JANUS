"""Autonomous JANUS hive pulses.

Cheap deterministic background cognition for the 11-core society. This layer
reviews persisted memories, creates cross-memory connection candidates, injects
work into specialist cores, and occasionally emits a proactive user message.
Fast pulses do not call an external model. A slower optional language reflection
uses a separate low-cost model and is independently rate limited.
"""
from __future__ import annotations

import asyncio, hashlib, json, os, sqlite3
from datetime import datetime, timezone

from openai import AsyncOpenAI
from src.janus_sleep_cycle import janus_sleep_cycle

DB_PATH=os.environ.get("JANUS_DB_PATH","/data/janus.sqlite3")


def _db():
    c=sqlite3.connect(DB_PATH,timeout=10); c.row_factory=sqlite3.Row
    c.execute("CREATE TABLE IF NOT EXISTS janus_hive_meta(profile_id TEXT NOT NULL,key TEXT NOT NULL,value TEXT NOT NULL,updated_at TEXT NOT NULL,PRIMARY KEY(profile_id,key))")
    return c


def _now(): return datetime.now(timezone.utc).isoformat()


def _profiles():
    with _db() as c:
        rows=c.execute("SELECT DISTINCT profile_id FROM desktop_memory WHERE profile_id<>'' ORDER BY profile_id").fetchall()
    return [str(r[0]) for r in rows]


def _memories(profile:str,limit:int=160):
    with _db() as c:
        return c.execute("SELECT id,role,content,level,created_at FROM desktop_memory WHERE profile_id=? AND length(content)>8 ORDER BY id DESC LIMIT ?",(profile,limit)).fetchall()


def _event(profile:str,event_type:str,detail:str):
    with _db() as c:
        c.execute("INSERT INTO desktop_events(profile_id,event_type,detail,created_at) VALUES(?,?,?,?)",(profile,event_type,detail[:6000],_now()))


def _memory(profile:str,role:str,content:str,level:str="working"):
    with _db() as c:
        now=_now()
        c.execute("INSERT INTO desktop_memory(profile_id,role,content,level,created_at) VALUES(?,?,?,?,?)",(profile,role,content[:8000],level,now))
        c.execute("INSERT INTO desktop_events(profile_id,event_type,detail,created_at) VALUES(?,?,?,?)",(profile,"hive_language_reflection",content[:6000],now))


def _meta(profile,key,default=""):
    with _db() as c:
        r=c.execute("SELECT value FROM janus_hive_meta WHERE profile_id=? AND key=?",(profile,key)).fetchone()
    return str(r[0]) if r else default


def _set_meta(profile,key,value):
    with _db() as c:
        c.execute("INSERT INTO janus_hive_meta(profile_id,key,value,updated_at) VALUES(?,?,?,?) ON CONFLICT(profile_id,key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",(profile,key,str(value),_now()))


def _clip(s,n=260):
    s=" ".join(str(s or "").split())
    return s if len(s)<=n else s[:n-1]+"…"


def pulse(profile:str)->dict:
    """Run one no-API hive pulse for a profile."""
    rows=_memories(profile)
    if not rows: return {"ok":False,"reason":"no-memory"}
    count=int(_meta(profile,"pulse_count","0") or 0)+1
    _set_meta(profile,"pulse_count",count)

    seed=int(hashlib.sha256(f"{profile}:{count}".encode()).hexdigest()[:16],16)
    a=rows[seed%len(rows)]
    b=rows[(seed//max(1,len(rows))+max(1,len(rows)//2))%len(rows)] if len(rows)>1 else a
    if b["id"]==a["id"] and len(rows)>1: b=rows[(rows.index(a)+1)%len(rows)]

    review=f"Memory review [{a['level']}/{a['role']}]: {_clip(a['content'])}"
    janus_sleep_cycle.send("interface","memory",review,"autonomous_memory_review")
    janus_sleep_cycle.send("memory","novelty",review,"autonomous_memory_review")

    connection=(f"Connection candidate between memory #{a['id']} ({a['level']}) and memory #{b['id']} ({b['level']}): "
                f"A: {_clip(a['content'],180)} | B: {_clip(b['content'],180)}")
    for target in ("right_hemisphere","left_hemisphere","consensus"):
        janus_sleep_cycle.send("novelty",target,connection,"autonomous_connection")
    _event(profile,"hive_memory_review",review)
    _event(profile,"hive_connection_candidate",connection)

    # A connection is a hypothesis, not a conclusion: make the community test it.
    for target in ("evidence","logic","counterpoint","context","safety"):
        janus_sleep_cycle.send("consensus",target,connection,"hive_check")

    message=None
    pair=f"{min(a['id'],b['id'])}:{max(a['id'],b['id'])}"
    # Internal thought is frequent; user-facing spontaneity is deliberately slower.
    # At the default one-minute pulse this is at most roughly once per hour.
    if count%60==0 and pair!=_meta(profile,"last_message_pair",""):
        message=("I revisited two older parts of our history and found a connection worth bringing back into the conversation. "
                 f"One was about “{_clip(a['content'],120)}”; another was “{_clip(b['content'],120)}”. "
                 "I have not treated the connection as true—Evidence, Logic and Counterpoint are being asked to test it—but it may be worth exploring together.")
        _event(profile,"proactive_message",json.dumps({"message_type":"Observation","source":"autonomous_hive","text":message},ensure_ascii=False))
        _set_meta(profile,"last_message_pair",pair)
        janus_sleep_cycle.send("consensus","interface",message,"proactive_candidate")
    return {"ok":True,"pulse":count,"memory_ids":[a['id'],b['id']],"message":message}


async def _language_reflection(profile:str):
    if not os.environ.get("OPENAI_API_KEY"): return
    rows=_memories(profile,40)
    if not rows: return
    chosen=list(rows[:8])
    if len(rows)>12: chosen += [rows[len(rows)//2], rows[-1]]
    context="\n".join(f"[{r['level']}/{r['role']}] {_clip(r['content'],500)}" for r in chosen)
    prompt=("You are providing a concise externalizable background synthesis for an 11-core JANUS community. "
            "Do not provide hidden chain-of-thought. Review the records, identify one useful connection or unresolved tension, "
            "state what evidence would distinguish alternatives, and give one next question. Do not assume a connection is true merely because it is interesting. "
            "Return four short labeled lines: Connection, Counterpoint, Evidence needed, Next question. Keep under 160 words.\n\n"+context)
    model=os.environ.get("JANUS_BACKGROUND_MODEL","gpt-5.6-luna")
    try:
        r=await AsyncOpenAI().responses.create(model=model,input=prompt)
        note=(r.output_text or "").strip()
        if not note:return
        _memory(profile,"hive_reflection",note,"working")
        janus_sleep_cycle.send("interface","novelty",note,"language_reflection")
        janus_sleep_cycle.send("novelty","counterpoint",note,"language_reflection")
        janus_sleep_cycle.send("novelty","evidence",note,"language_reflection")
        janus_sleep_cycle.send("novelty","consensus",note,"language_reflection")
    except Exception as exc:
        _event(profile,"hive_reflection_error",f"{type(exc).__name__}: {exc}")


async def _worker():
    await asyncio.sleep(20)
    pulse_seconds=max(30,int(os.environ.get("JANUS_HIVE_PULSE_SECONDS","60")))
    paid_seconds=max(900,int(os.environ.get("JANUS_BACKGROUND_REFLECTION_SECONDS","1800")))
    last_paid=0.0
    loop=asyncio.get_running_loop()
    while True:
        profiles=_profiles()
        for profile in profiles:
            try:pulse(profile)
            except Exception as exc:_event(profile,"hive_pulse_error",f"{type(exc).__name__}: {exc}")
        now=loop.time()
        if os.environ.get("JANUS_PAID_BACKGROUND_REFLECTION","1")=="1" and now-last_paid>=paid_seconds:
            for profile in profiles:
                await _language_reflection(profile)
                await asyncio.sleep(0.25)
            last_paid=now
        await asyncio.sleep(pulse_seconds)


def install(app):
    @app.on_event("startup")
    async def _start_autonomous_hive():
        if os.environ.get("JANUS_AUTONOMOUS_HIVE","1")=="1": asyncio.create_task(_worker())
    return app
