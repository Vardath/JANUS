"""Selective federated memory synchronization for JANUS.

Local/device state is never wholesale-replaced. Devices exchange bounded, typed
records with provenance and stable origin ids. The server stores remote records as
remote evidence, detects conflicting current claims, and exposes bounded outbound
records for specialist review. Protected identity/core state is never accepted from
remote peers.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any

DB_PATH=os.environ.get("JANUS_DB_PATH","/data/janus.sqlite3")
MAX_IN=max(1,min(48,int(os.environ.get("JANUS_FEDERATED_MAX_INBOUND","16"))))
MAX_OUT=max(1,min(48,int(os.environ.get("JANUS_FEDERATED_MAX_OUTBOUND","12"))))
ALLOWED_KINDS={"memory","conclusion","question","project","research","correction","preference","observation"}
BLOCKED_KINDS={"identity_core","system","policy","credential","secret","auth"}
CURRENT_STATES={"proposed","approved","active","investigating","testing","blocked","provisional","reopened"}


def _now(): return datetime.now(timezone.utc).isoformat()

def _db():
 c=sqlite3.connect(DB_PATH,timeout=15); c.row_factory=sqlite3.Row; c.execute("PRAGMA journal_mode=WAL")
 c.executescript("""
 CREATE TABLE IF NOT EXISTS janus_federated_records(
   id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id TEXT NOT NULL, origin_device TEXT NOT NULL,
   origin_id TEXT NOT NULL, kind TEXT NOT NULL, text TEXT NOT NULL, state TEXT NOT NULL DEFAULT '',
   confidence REAL NOT NULL DEFAULT 0.5, source_updated_at TEXT NOT NULL DEFAULT '',
   content_hash TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'accepted', conflict_group TEXT NOT NULL DEFAULT '',
   created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
   UNIQUE(profile_id,origin_device,origin_id)
 );
 CREATE INDEX IF NOT EXISTS idx_fed_profile_updated ON janus_federated_records(profile_id,updated_at DESC);
 CREATE TABLE IF NOT EXISTS janus_federated_conflicts(
   id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id TEXT NOT NULL, conflict_group TEXT NOT NULL,
   left_record INTEGER NOT NULL, right_record INTEGER NOT NULL, reason TEXT NOT NULL,
   status TEXT NOT NULL DEFAULT 'open', created_at TEXT NOT NULL,
   UNIQUE(profile_id,left_record,right_record)
 );
 """); return c

def _norm(s:str)->str: return " ".join(str(s or "").lower().split())
def _tokens(s:str)->set[str]: return set(re.findall(r"[a-z0-9][a-z0-9_-]{2,}",_norm(s)))
def _hash(kind:str,text:str,state:str)->str: return hashlib.sha256(f"{kind}|{_norm(text)}|{state}".encode()).hexdigest()
def _group(kind:str,text:str)->str:
 toks=sorted(_tokens(text))[:10]
 return hashlib.sha256((kind+"|"+" ".join(toks)).encode()).hexdigest()[:20] if toks else ""

def _validate_record(raw:dict[str,Any],device_id:str)->dict[str,Any]|None:
 kind=str(raw.get("kind") or "memory").strip().lower()
 if kind in BLOCKED_KINDS or kind not in ALLOWED_KINDS: return None
 text=" ".join(str(raw.get("text") or "").split()).strip()
 if len(text)<8:return None
 origin_id=str(raw.get("origin_id") or raw.get("id") or _hash(kind,text,str(raw.get('state') or ''))[:24])[:128]
 state=str(raw.get("state") or "")[:32]
 try: confidence=max(0.0,min(1.0,float(raw.get("confidence",0.5))))
 except Exception: confidence=0.5
 return {"origin_device":device_id[:128],"origin_id":origin_id,"kind":kind,"text":text[:4000],"state":state,
         "confidence":confidence,"source_updated_at":str(raw.get("updated_at") or raw.get("created_at") or "")[:64]}

def _semantic_conflict(a:sqlite3.Row,b:dict[str,Any])->bool:
 if a["kind"]!=b["kind"]:return False
 ta,tb=_tokens(a["text"]),_tokens(b["text"])
 if not ta or not tb:return False
 overlap=len(ta&tb)/max(1,min(len(ta),len(tb)))
 if overlap<0.45:return False
 sa,sb=str(a["state"] or ""),str(b["state"] or "")
 if sa and sb and sa!=sb and (sa in CURRENT_STATES or sb in CURRENT_STATES): return True
 negatives=(" not "," no "," never "," wrong "," false "," replaced "," supersed")
 na=any(x in " "+_norm(a["text"])+" " for x in negatives); nb=any(x in " "+_norm(b["text"])+" " for x in negatives)
 return na!=nb and overlap>=0.6

def ingest(profile_id:str,device_id:str,records:list[dict[str,Any]]|None)->dict[str,Any]:
 accepted=updated=ignored=conflicts=0; accepted_items=[]
 for raw in (records or [])[:MAX_IN]:
  if not isinstance(raw,dict): ignored+=1; continue
  r=_validate_record(raw,device_id)
  if not r: ignored+=1; continue
  h=_hash(r["kind"],r["text"],r["state"]); now=_now(); group=_group(r["kind"],r["text"])
  with _db() as c:
   existing=c.execute("SELECT * FROM janus_federated_records WHERE profile_id=? AND origin_device=? AND origin_id=?",(profile_id,device_id,r["origin_id"])).fetchone()
   if existing and existing["content_hash"]==h: ignored+=1; continue
   if existing:
    c.execute("UPDATE janus_federated_records SET kind=?,text=?,state=?,confidence=?,source_updated_at=?,content_hash=?,updated_at=? WHERE id=?",
      (r["kind"],r["text"],r["state"],r["confidence"],r["source_updated_at"],h,now,existing["id"])); record_id=int(existing["id"]); updated+=1
   else:
    cur=c.execute("INSERT INTO janus_federated_records(profile_id,origin_device,origin_id,kind,text,state,confidence,source_updated_at,content_hash,conflict_group,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
      (profile_id,device_id,r["origin_id"],r["kind"],r["text"],r["state"],r["confidence"],r["source_updated_at"],h,group,now,now)); record_id=int(cur.lastrowid); accepted+=1
   record_conflicted=False
   peers=c.execute("SELECT * FROM janus_federated_records WHERE profile_id=? AND id<>? AND kind=? ORDER BY updated_at DESC LIMIT 80",(profile_id,record_id,r["kind"])).fetchall()
   for p in peers:
    if _semantic_conflict(p,r):
     left,right=sorted((int(p["id"]),record_id)); cg=group or _group(r["kind"],r["text"])
     c.execute("INSERT OR IGNORE INTO janus_federated_conflicts(profile_id,conflict_group,left_record,right_record,reason,created_at) VALUES(?,?,?,?,?,?)",
       (profile_id,cg,left,right,"similar federated records disagree in lifecycle/claim polarity",now))
     c.execute("UPDATE janus_federated_records SET status='conflicted',conflict_group=? WHERE id IN (?,?)",(cg,left,right)); conflicts+=1; record_conflicted=True
   c.commit()
  accepted_items.append({**r,"record_id":record_id,"status":"conflicted" if record_conflicted else "accepted","merge_policy":"grounding_only_no_overwrite"})
 return {"accepted":accepted,"updated":updated,"ignored":ignored,"conflicts":conflicts,"accepted_items":accepted_items[:MAX_IN]}

def outbound(profile_id:str,exclude_device:str="",limit:int=MAX_OUT)->list[dict[str,Any]]:
 """Return bounded shared records. They are grounding candidates, never overwrite commands."""
 items=[]
 try:
  with _db() as c:
   rows=c.execute("SELECT id,origin_device,origin_id,kind,text,state,confidence,status,updated_at FROM janus_federated_records WHERE profile_id=? AND origin_device<>? ORDER BY CASE status WHEN 'accepted' THEN 0 ELSE 1 END, confidence DESC, updated_at DESC LIMIT ?",
    (profile_id,exclude_device,max(1,min(MAX_OUT,int(limit))))).fetchall()
  for r in rows:
   items.append({"record_id":int(r["id"]),"origin_device":r["origin_device"],"origin_id":r["origin_id"],"kind":r["kind"],"text":r["text"],"state":r["state"],"confidence":float(r["confidence"]),"status":r["status"],"updated_at":r["updated_at"],"merge_policy":"grounding_only_no_overwrite"})
 except Exception: pass
 return items

def conflict_status(profile_id:str,limit:int=50)->list[dict[str,Any]]:
 try:
  with _db() as c:
   rows=c.execute("SELECT * FROM janus_federated_conflicts WHERE profile_id=? ORDER BY id DESC LIMIT ?",(profile_id,max(1,min(200,int(limit))))).fetchall()
  return [dict(r) for r in rows]
 except Exception:return []
