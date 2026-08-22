"""Unified per-profile JANUS external-compute accounting and budget governor.

All paid/external model, web, vision and image calls can be classified into a small
set of capabilities.  The governor records reservations + observed usage, enforces
per-profile daily/monthly estimated-cost limits, and deliberately degrades optional
background work before foreground chat.

The USD figures are estimates driven by environment-configurable reservation rates;
they are budgeting signals, not billing statements from the provider.
"""
from __future__ import annotations

import contextlib
import contextvars
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_PATH=os.environ.get("JANUS_DB_PATH","/data/janus.sqlite3")
_current_profile=contextvars.ContextVar("janus_cost_profile",default="__unattributed__")
_current_capability=contextvars.ContextVar("janus_cost_capability",default="chat")

CAPABILITIES={"chat","foreground_core","background_model","background_web","vision","image","maintenance","other"}
OPTIONAL={"background_model","background_web","maintenance"}
DEFAULT_RESERVATION_USD={
 "chat":0.03,"foreground_core":0.02,"background_model":0.01,"background_web":0.02,
 "vision":0.012,"image":0.06,"maintenance":0.01,"other":0.01,
}

def _float_env(name:str,default:float)->float:
 try:return max(0.0,float(os.environ.get(name,str(default))))
 except Exception:return default

PROFILE_DAILY_USD=_float_env("JANUS_COST_PROFILE_DAILY_USD",2.00)
PROFILE_MONTHLY_USD=_float_env("JANUS_COST_PROFILE_MONTHLY_USD",30.00)
BACKGROUND_DAILY_USD=_float_env("JANUS_COST_BACKGROUND_DAILY_USD",0.50)
GLOBAL_DAILY_USD=_float_env("JANUS_COST_GLOBAL_DAILY_USD",100.0)


def _db():
 p=Path(os.environ.get("JANUS_DB_PATH",DB_PATH)); p.parent.mkdir(parents=True,exist_ok=True)
 c=sqlite3.connect(p,timeout=15); c.row_factory=sqlite3.Row; c.execute("PRAGMA journal_mode=WAL")
 c.executescript("""
 CREATE TABLE IF NOT EXISTS janus_cost_events(
  id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id TEXT NOT NULL, capability TEXT NOT NULL,
  model TEXT NOT NULL DEFAULT '', estimated_usd REAL NOT NULL DEFAULT 0,
  input_tokens INTEGER NOT NULL DEFAULT 0, output_tokens INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'complete', detail TEXT NOT NULL DEFAULT '', created_at INTEGER NOT NULL
 );
 CREATE INDEX IF NOT EXISTS idx_cost_profile_time ON janus_cost_events(profile_id,created_at);
 CREATE INDEX IF NOT EXISTS idx_cost_cap_time ON janus_cost_events(capability,created_at);
 CREATE TABLE IF NOT EXISTS janus_cost_denials(
  id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id TEXT NOT NULL, capability TEXT NOT NULL,
  reason TEXT NOT NULL, estimated_usd REAL NOT NULL DEFAULT 0, created_at INTEGER NOT NULL
 );
 """); return c


def _reservation(capability:str)->float:
 cap=capability if capability in CAPABILITIES else "other"
 return _float_env("JANUS_COST_RESERVE_"+cap.upper()+"_USD",DEFAULT_RESERVATION_USD[cap])

def _bounds(now:int|None=None):
 now=int(now or time.time()); dt=datetime.fromtimestamp(now,tz=timezone.utc)
 day=int(datetime(dt.year,dt.month,dt.day,tzinfo=timezone.utc).timestamp())
 month=int(datetime(dt.year,dt.month,1,tzinfo=timezone.utc).timestamp())
 return day,month

def _sum(profile:str|None,start:int,capabilities:set[str]|None=None)->float:
 with _db() as c:
  if profile is None:
   row=c.execute("SELECT COALESCE(SUM(estimated_usd),0) FROM janus_cost_events WHERE created_at>=? AND status<>'cancelled'",(start,)).fetchone()
  elif capabilities:
   marks=",".join("?" for _ in capabilities)
   row=c.execute(f"SELECT COALESCE(SUM(estimated_usd),0) FROM janus_cost_events WHERE profile_id=? AND created_at>=? AND status<>'cancelled' AND capability IN ({marks})",[profile,start,*sorted(capabilities)]).fetchone()
  else:
   row=c.execute("SELECT COALESCE(SUM(estimated_usd),0) FROM janus_cost_events WHERE profile_id=? AND created_at>=? AND status<>'cancelled'",(profile,start)).fetchone()
 return float(row[0] or 0.0)

def authorize(profile_id:str,capability:str,estimated_usd:float|None=None)->dict[str,Any]:
 profile=str(profile_id or "__unattributed__")[:160]; cap=capability if capability in CAPABILITIES else "other"
 reserve=_reservation(cap) if estimated_usd is None else max(0.0,float(estimated_usd)); now=int(time.time()); day,month=_bounds(now)
 daily=_sum(profile,day); monthly=_sum(profile,month); global_daily=_sum(None,day); background=_sum(profile,day,OPTIONAL)
 reason=""
 if GLOBAL_DAILY_USD and global_daily+reserve>GLOBAL_DAILY_USD: reason="global daily external-compute budget reached"
 elif PROFILE_MONTHLY_USD and monthly+reserve>PROFILE_MONTHLY_USD: reason="profile monthly external-compute budget reached"
 elif PROFILE_DAILY_USD and daily+reserve>PROFILE_DAILY_USD: reason="profile daily external-compute budget reached"
 elif cap in OPTIONAL and BACKGROUND_DAILY_USD and background+reserve>BACKGROUND_DAILY_USD: reason="background daily budget reached"
 if reason:
  with _db() as c:c.execute("INSERT INTO janus_cost_denials(profile_id,capability,reason,estimated_usd,created_at) VALUES(?,?,?,?,?)",(profile,cap,reason,reserve,now))
  return {"allowed":False,"reason":reason,"reserve_usd":reserve,"daily_estimated_usd":round(daily,6),"monthly_estimated_usd":round(monthly,6)}
 return {"allowed":True,"reason":"ok","reserve_usd":reserve,"daily_estimated_usd":round(daily,6),"monthly_estimated_usd":round(monthly,6)}

def _usage_tokens(response:Any)->tuple[int,int]:
 try:
  u=getattr(response,"usage",None)
  if not u:return 0,0
  inp=int(getattr(u,"input_tokens",0) or 0); out=int(getattr(u,"output_tokens",0) or 0)
  return inp,out
 except Exception:return 0,0

def record(profile_id:str,capability:str,*,model:str="",estimated_usd:float|None=None,response:Any=None,status:str="complete",detail:str="")->int:
 cap=capability if capability in CAPABILITIES else "other"; profile=str(profile_id or "__unattributed__")[:160]
 usd=_reservation(cap) if estimated_usd is None else max(0.0,float(estimated_usd)); inp,out=_usage_tokens(response)
 with _db() as c:
  cur=c.execute("INSERT INTO janus_cost_events(profile_id,capability,model,estimated_usd,input_tokens,output_tokens,status,detail,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
   (profile,cap,str(model or "")[:120],usd,inp,out,str(status)[:32],str(detail)[:1000],int(time.time())))
  return int(cur.lastrowid)

def status(profile_id:str)->dict[str,Any]:
 profile=str(profile_id or "__unattributed__")[:160]; now=int(time.time()); day,month=_bounds(now)
 daily=_sum(profile,day); monthly=_sum(profile,month); background=_sum(profile,day,OPTIONAL)
 with _db() as c:
  rows=c.execute("SELECT capability,COUNT(*) calls,COALESCE(SUM(estimated_usd),0) usd,COALESCE(SUM(input_tokens),0) input_tokens,COALESCE(SUM(output_tokens),0) output_tokens FROM janus_cost_events WHERE profile_id=? AND created_at>=? GROUP BY capability ORDER BY usd DESC",(profile,day)).fetchall()
  denied=c.execute("SELECT COUNT(*) FROM janus_cost_denials WHERE profile_id=? AND created_at>=?",(profile,day)).fetchone()[0]
 return {"profile_id":profile,"today_estimated_usd":round(daily,6),"month_estimated_usd":round(monthly,6),"background_today_estimated_usd":round(background,6),"daily_limit_usd":PROFILE_DAILY_USD,"monthly_limit_usd":PROFILE_MONTHLY_USD,"background_daily_limit_usd":BACKGROUND_DAILY_USD,"denied_today":int(denied or 0),"by_capability":[dict(r) for r in rows],"estimate_notice":"Budget estimates are configurable planning values, not provider invoices."}

@contextlib.contextmanager
def scope(profile_id:str,capability:str):
 a=_current_profile.set(str(profile_id or "__unattributed__")); b=_current_capability.set(capability if capability in CAPABILITIES else "other")
 try:yield
 finally:_current_profile.reset(a); _current_capability.reset(b)

def current()->tuple[str,str]: return _current_profile.get(),_current_capability.get()

def authorize_current()->dict[str,Any]:
 p,c=current(); return authorize(p,c)

def record_current(*,model:str="",response:Any=None,status:str="complete",detail:str="")->int:
 p,c=current(); return record(p,c,model=model,response=response,status=status,detail=detail)
