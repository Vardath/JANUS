"""Persistent zero-API-cost 11-core JANUS runtime with a Fano/JANUS unit inside every core."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
import json, os, sqlite3, threading, time

from src.fano_core import FanoJanusUnit

SPECIALIST_CORES=("evidence","logic","counterpoint","context","memory","safety","novelty")
HEMISPHERE_CORES=("left_hemisphere","right_hemisphere")
CONSENSUS_CORE="consensus"; INTERFACE_CORE="interface"
CORE_NAMES=SPECIALIST_CORES+HEMISPHERE_CORES+(CONSENSUS_CORE,INTERFACE_CORE)
CORE_GROUPS={
    "specialists":set(SPECIALIST_CORES),
    "left":{"evidence","logic","counterpoint","left_hemisphere"},
    "right":{"context","memory","novelty","right_hemisphere"},
    "safety":{"safety","left_hemisphere","right_hemisphere","consensus"},
    "hemispheres":set(HEMISPHERE_CORES),
    "integration":{"left_hemisphere","right_hemisphere","consensus","interface"},
    "all":set(CORE_NAMES),
}
DB_PATH=os.environ.get("JANUS_DB_PATH","/data/janus.sqlite3")
CHECKPOINT_SECONDS=max(10,int(os.environ.get("JANUS_CORE_CHECKPOINT_SECONDS","30")))

@dataclass
class CoreMessage:
    sender:str; recipient:str; kind:str; content:str; group:Optional[str]=None
    created_at:str=field(default_factory=lambda:datetime.now(timezone.utc).isoformat())

@dataclass
class CoreState:
    name:str
    awake:bool=False
    cycle_count:int=0
    thoughts:List[str]=field(default_factory=list)
    inbox:List[CoreMessage]=field(default_factory=list)
    last_cycle_at:Optional[str]=None
    last_output:str=""
    fano:FanoJanusUnit=field(default_factory=FanoJanusUnit)

class JanusSleepCycle:
    def __init__(self,wake_seconds:int=300,sleep_seconds:int=600,local_thinker=None)->None:
        self.wake_seconds=max(10,int(wake_seconds)); self.sleep_seconds=max(10,int(sleep_seconds))
        self.cores:Dict[str,CoreState]={n:CoreState(n) for n in CORE_NAMES}
        self._stop=threading.Event(); self._thread=None; self._phase="sleep"; self._phase_started_at=time.time()
        self._lock=threading.RLock(); self._last_consensus=""; self._last_interface=""; self._remote_summaries={}
        self._last_checkpoint=0.0; self._persistence_ready=False; self._last_burst_at=None; self._burst_count=0
        self._init_persistence(); self._restore_state(); self.cores[INTERFACE_CORE].awake=True

    def _db(self):
        c=sqlite3.connect(DB_PATH,timeout=10); c.row_factory=sqlite3.Row; c.execute("PRAGMA journal_mode=WAL"); return c

    def _init_persistence(self):
        try:
            os.makedirs(os.path.dirname(DB_PATH) or ".",exist_ok=True)
            with self._db() as c:
                c.executescript("""
                CREATE TABLE IF NOT EXISTS janus_core_runtime_state(
                    core_name TEXT PRIMARY KEY,cycle_count INTEGER NOT NULL DEFAULT 0,awake INTEGER NOT NULL DEFAULT 0,
                    thoughts_json TEXT NOT NULL DEFAULT '[]',inbox_json TEXT NOT NULL DEFAULT '[]',last_cycle_at TEXT,
                    last_output TEXT NOT NULL DEFAULT '',fano_json TEXT NOT NULL DEFAULT '{}',updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS janus_core_runtime_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL,updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS janus_core_remote_summary(device_id TEXT PRIMARY KEY,summary_json TEXT NOT NULL,updated_at TEXT NOT NULL);
                """)
                cols={r[1] for r in c.execute("PRAGMA table_info(janus_core_runtime_state)")}
                if "fano_json" not in cols:c.execute("ALTER TABLE janus_core_runtime_state ADD COLUMN fano_json TEXT NOT NULL DEFAULT '{}'")
            self._persistence_ready=True
        except Exception:self._persistence_ready=False

    def _restore_state(self):
        if not self._persistence_ready:return
        try:
            with self._db() as c:
                for r in c.execute("SELECT * FROM janus_core_runtime_state"):
                    n=str(r["core_name"])
                    if n not in self.cores:continue
                    x=self.cores[n]; x.cycle_count=int(r["cycle_count"] or 0); x.awake=bool(r["awake"]); x.last_cycle_at=r["last_cycle_at"]; x.last_output=str(r["last_output"] or "")
                    try:x.thoughts=[str(v) for v in json.loads(r["thoughts_json"] or "[]")][-64:]
                    except Exception:x.thoughts=[]
                    try:x.fano=FanoJanusUnit.from_dict(json.loads(r["fano_json"] or "{}"))
                    except Exception:x.fano=FanoJanusUnit()
                    try:x.inbox=[CoreMessage(str(m.get("sender") or "unknown")[:64],n,str(m.get("kind") or "restored")[:64],str(m.get("content") or "")[:4000],str(m.get("group"))[:64] if m.get("group") is not None else None,str(m.get("created_at") or datetime.now(timezone.utc).isoformat())) for m in json.loads(r["inbox_json"] or "[]")[-128:] if isinstance(m,dict)]
                    except Exception:x.inbox=[]
                meta={r["key"]:r["value"] for r in c.execute("SELECT key,value FROM janus_core_runtime_meta")}
                self._phase=str(meta.get("phase") or "sleep"); self._last_consensus=str(meta.get("last_consensus") or ""); self._last_interface=str(meta.get("last_interface") or "")
                self._last_burst_at=meta.get("last_burst_at") or None; self._burst_count=int(meta.get("burst_count") or 0)
                for r in c.execute("SELECT device_id,summary_json FROM janus_core_remote_summary"):
                    try:self._remote_summaries[str(r["device_id"])]=json.loads(r["summary_json"])
                    except Exception:pass
        except Exception:pass

    def checkpoint(self,force:bool=False)->bool:
        if not self._persistence_ready:return False
        now=time.monotonic()
        if not force and now-self._last_checkpoint<CHECKPOINT_SECONDS:return True
        stamp=datetime.now(timezone.utc).isoformat()
        try:
            with self._lock,self._db() as c:
                for n,x in self.cores.items():
                    c.execute("""INSERT INTO janus_core_runtime_state(core_name,cycle_count,awake,thoughts_json,inbox_json,last_cycle_at,last_output,fano_json,updated_at)
                    VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(core_name) DO UPDATE SET cycle_count=excluded.cycle_count,awake=excluded.awake,thoughts_json=excluded.thoughts_json,inbox_json=excluded.inbox_json,last_cycle_at=excluded.last_cycle_at,last_output=excluded.last_output,fano_json=excluded.fano_json,updated_at=excluded.updated_at""",
                    (n,x.cycle_count,1 if x.awake else 0,json.dumps(x.thoughts[-64:]),json.dumps([asdict(m) for m in x.inbox[-128:]]),x.last_cycle_at,x.last_output[-4000:],json.dumps(x.fano.summary()),stamp))
                meta={"phase":self._phase,"last_consensus":self._last_consensus[-4000:],"last_interface":self._last_interface[-4000:],"last_burst_at":self._last_burst_at or "","burst_count":str(self._burst_count)}
                for k,v in meta.items():c.execute("INSERT INTO janus_core_runtime_meta(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",(k,v,stamp))
                for d,s in list(self._remote_summaries.items())[-100:]:c.execute("INSERT INTO janus_core_remote_summary(device_id,summary_json,updated_at) VALUES(?,?,?) ON CONFLICT(device_id) DO UPDATE SET summary_json=excluded.summary_json,updated_at=excluded.updated_at",(d,json.dumps(s),stamp))
            self._last_checkpoint=now; return True
        except Exception:return False

    @property
    def phase(self):return self._phase
    def start(self):
        if self._thread and self._thread.is_alive():return
        self._stop.clear(); self._thread=threading.Thread(target=self._run,name="janus-11-fano-cycle",daemon=True); self._thread.start()
    def stop(self):self._stop.set(); self.checkpoint(True)

    def send(self,sender,recipient,content,kind="peer"):
        if sender in self.cores and recipient in self.cores:
            with self._lock:self.cores[recipient].inbox.append(CoreMessage(sender,recipient,kind,str(content)[:4000]))
    def send_group(self,sender,group,content,kind="group"):
        for r in CORE_GROUPS.get(group,set()):
            if r!=sender:self.send(sender,r,content,kind)
    def broadcast(self,sender,content,kind="broadcast"):self.send_group(sender,"all",content,kind)

    def accept_remote_summary(self,device_id,summary):
        clean={"received_at":datetime.now(timezone.utc).isoformat(),"phase":str(summary.get("phase") or "unknown")[:32],"consensus":str(summary.get("consensus") or "")[:1000],"interface":str(summary.get("interface") or "")[:1000],"cycles":dict(summary.get("cycles") or {})}
        self._remote_summaries[str(device_id)[:128]]=clean; self.send("interface","consensus",f"client-sync {device_id}: {clean['consensus']}","client_sync"); self.checkpoint()

    def compact_summary(self):
        return {"architecture":"11 Fano/JANUS cores","topology":"7 -> 2 -> 1 -> 1","phase":self._phase,"background_phase":self._phase,"interface_available":True,"consensus":self._last_consensus,"interface":self._last_interface,"cycles":{n:x.cycle_count for n,x in self.cores.items()},"fano":{n:x.fano.summary() for n,x in self.cores.items()},"persistent":self._persistence_ready,"burst_count":self._burst_count,"last_burst_at":self._last_burst_at}

    def status(self):
        with self._lock:
            return {"architecture":"11 Fano/JANUS cores","topology":"7 -> 2 -> 1 -> 1","core_count":11,"phase":self._phase,"background_phase":self._phase,"interface_available":True,"wake_seconds":self.wake_seconds,"sleep_seconds":self.sleep_seconds,"external_api_budget_used":0,"persistent_storage":self._persistence_ready,"storage_backend":"sqlite-render-disk" if self._persistence_ready else "memory-only","database_path":DB_PATH,"checkpoint_seconds":CHECKPOINT_SECONDS,"last_consensus":self._last_consensus,"last_interface":self._last_interface,"remote_clients":len(self._remote_summaries),"burst_count":self._burst_count,"last_burst_at":self._last_burst_at,"groups":{k:sorted(v) for k,v in CORE_GROUPS.items()},"cores":{n:{"awake":x.awake,"cycle_count":x.cycle_count,"pending_messages":len(x.inbox),"last_cycle_at":x.last_cycle_at,"last_output":x.last_output[-300:],"fano":x.fano.summary()} for n,x in self.cores.items()}}

    def _run(self):
        while not self._stop.is_set():
            self._enter_phase("wake"); self._run_wake_window()
            if self._stop.is_set():break
            self._enter_phase("sleep"); self._run_sleep_window()
        self.checkpoint(True)
    def _enter_phase(self,p):
        self._phase=p
        for x in self.cores.values():x.awake=(p=="wake" or x.name==INTERFACE_CORE)
        self.checkpoint(True)
    def _cycle_core(self,n):
        x=self.cores[n]; incoming=list(x.inbox); x.inbox.clear(); thought=self._think(x,incoming)
        x.thoughts.append(thought); x.thoughts=x.thoughts[-64:]; x.last_output=thought; x.cycle_count+=1; x.last_cycle_at=datetime.now(timezone.utc).isoformat(); self._route_output(n,thought)

    def service_work_burst(self,include_interface:bool=True,only_if_pending:bool=True)->dict:
        """Briefly wake and process a complete 7→2→1→1 work pass.

        Used by autonomous hive pulses during society rest. Cores return to their
        previous awake/resting state afterwards, so rest remains meaningful while
        pending work is never forced to wait for a full wake window.
        """
        order=(SPECIALIST_CORES,HEMISPHERE_CORES,(CONSENSUS_CORE,),(INTERFACE_CORE,) if include_interface else tuple())
        processed=[]; previous={}
        with self._lock:
            for stage in order:
                for n in stage:
                    x=self.cores[n]
                    if only_if_pending and not x.inbox:continue
                    previous.setdefault(n,x.awake); x.awake=True; self._cycle_core(n); processed.append(n)
            for n,was_awake in previous.items():
                self.cores[n].awake=True if n==INTERFACE_CORE else was_awake
            if processed:
                self._burst_count+=1; self._last_burst_at=datetime.now(timezone.utc).isoformat()
        if processed:self.checkpoint(True)
        return {"processed":processed,"count":len(processed),"burst_count":self._burst_count,"at":self._last_burst_at}

    def _run_wake_window(self):
        deadline=time.monotonic()+self.wake_seconds
        while time.monotonic()<deadline and not self._stop.is_set():
            with self._lock:
                for n in CORE_NAMES:self._cycle_core(n)
            self.checkpoint(); time.sleep(5)
    def _run_sleep_window(self):
        for x in self.cores.values():x.thoughts=x.thoughts[-16:]
        self.cores[INTERFACE_CORE].awake=True
        self.checkpoint(True); deadline=time.monotonic()+self.sleep_seconds
        while time.monotonic()<deadline and not self._stop.is_set():
            with self._lock:
                if self.cores[INTERFACE_CORE].inbox:self._cycle_core(INTERFACE_CORE)
            self.checkpoint(); time.sleep(5)

    def _think(self,x:CoreState,incoming:List[CoreMessage])->str:
        texts=[m.content for m in incoming] or [x.last_output or x.name]
        x.fano.ingest(texts,x.name)
        f=x.fano.summary(); p=f["projection_1_3_4"]
        senders=sorted({m.sender for m in incoming})
        prefix={"left_hemisphere":"analytic hemisphere","right_hemisphere":"contextual hemisphere","consensus":"consensus reader/giver","interface":"main interface"}.get(x.name,x.name)
        peer=f" from {', '.join(senders)}" if senders else ""
        return f"{prefix}: Fano d{f['active_direction']} 1|3|4={p['origin']}|{p['line']}|{p['off_line']}; processed {len(incoming)} peer inputs{peer}"

    def _route_output(self,sender,content):
        if sender in {"evidence","logic","counterpoint"}:self.send(sender,"left_hemisphere",content,"specialist")
        elif sender in {"context","memory","novelty"}:self.send(sender,"right_hemisphere",content,"specialist")
        elif sender=="safety":self.send_group(sender,"integration",content,"safety")
        elif sender in HEMISPHERE_CORES:
            other="right_hemisphere" if sender=="left_hemisphere" else "left_hemisphere"; self.send(sender,other,content,"cross_hemisphere"); self.send(sender,"consensus",content,"hemisphere")
        elif sender=="consensus":self._last_consensus=content; self.send(sender,"interface",content,"consensus"); self.send_group(sender,"hemispheres",content,"feedback")
        elif sender=="interface":self._last_interface=content; self.send(sender,"consensus",content,"interface_feedback")

janus_sleep_cycle=JanusSleepCycle()
