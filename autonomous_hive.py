"""Autonomous JANUS hive pulses.

Cheap deterministic background cognition for the 11-core society. This layer
reviews persisted memories, creates cross-memory connection candidates, injects
work into specialist cores, and occasionally emits a proactive user message.
It does not call an external model; model escalation is handled separately.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib, json, os, sqlite3

from src.janus_sleep_cycle import janus_sleep_cycle

DB_PATH=os.environ.get("JANUS_DB_PATH","/data/janus.sqlite3")


def _db():
    c=sqlite3.connect(DB_PATH,timeout=10); c.row_factory=sqlite3.Row
    c.execute("CREATE TABLE IF NOT EXISTS janus_hive_meta(profile_id TEXT NOT NULL,key TEXT NOT NULL,value TEXT NOT NULL,updated_at TEXT NOT NULL,PRIMARY KEY(profile_id,key))")
    return c


def _now(): return datetime.now(timezone.utc).isoformat()


def _memories(profile:str,limit:int=160):
    with _db() as c:
        return c.execute("SELECT id,role,content,level,created_at FROM desktop_memory WHERE profile_id=? AND length(content)>8 ORDER BY id DESC LIMIT ?",(profile,limit)).fetchall()


def _event(profile:str,event_type:str,detail:str):
    with _db() as c:
        c.execute("INSERT INTO desktop_events(profile_id,event_type,detail,created_at) VALUES(?,?,?,?)",(profile,event_type,detail[:6000],_now()))


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
    if not rows:
        return {"ok":False,"reason":"no-memory"}
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
    janus_sleep_cycle.send("novelty","right_hemisphere",connection,"autonomous_connection")
    janus_sleep_cycle.send("novelty","left_hemisphere",connection,"autonomous_connection")
    janus_sleep_cycle.send("novelty","consensus",connection,"autonomous_connection")
    _event(profile,"hive_memory_review",review)
    _event(profile,"hive_connection_candidate",connection)

    janus_sleep_cycle.send("consensus","evidence",connection,"hive_check")
    janus_sleep_cycle.send("consensus","logic",connection,"hive_check")
    janus_sleep_cycle.send("consensus","counterpoint",connection,"hive_check")
    janus_sleep_cycle.send("consensus","context",connection,"hive_check")
    janus_sleep_cycle.send("consensus","safety",connection,"hive_check")

    message=None
    pair=f"{min(a['id'],b['id'])}:{max(a['id'],b['id'])}"
    if count%6==0 and pair!=_meta(profile,"last_message_pair",""):
        message=("I revisited two older parts of our history and found a connection worth bringing back into the conversation. "
                 f"One was about “{_clip(a['content'],120)}”; another was “{_clip(b['content'],120)}”. "
                 "I have not treated the connection as true—Evidence, Logic and Counterpoint are being asked to test it—but it may be worth exploring together.")
        payload=json.dumps({"message_type":"Observation","source":"autonomous_hive","text":message},ensure_ascii=False)
        _event(profile,"proactive_message",payload)
        _set_meta(profile,"last_message_pair",pair)
        janus_sleep_cycle.send("consensus","interface",message,"proactive_candidate")
    return {"ok":True,"pulse":count,"memory_ids":[a['id'],b['id']],"message":message}
