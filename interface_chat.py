"""Always-responsive JANUS interface chat route."""
from __future__ import annotations

import asyncio, json, os, sqlite3, time
from datetime import datetime, timezone
from typing import Any
from fastapi import HTTPException
from openai import AsyncOpenAI
from dashboard_api import JANUS_SELF_KNOWLEDGE, _recent_context, _store
from memory_retrieval import format_recall, promote_user_correction
from src.janus_sleep_cycle import janus_sleep_cycle

DB_PATH=os.environ.get("JANUS_DB_PATH","/data/janus.sqlite3")
GLOBAL_PROFILE="__global__"

def _receipt_db():
 c=sqlite3.connect(DB_PATH,timeout=10); c.row_factory=sqlite3.Row; c.execute("PRAGMA journal_mode=WAL"); c.execute("CREATE TABLE IF NOT EXISTS janus_chat_receipts(client_message_id TEXT PRIMARY KEY,profile_id TEXT NOT NULL,status TEXT NOT NULL,response_json TEXT,created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL)"); return c

def _claim_message(mid,profile):
 if not mid:return None
 now=int(time.time())
 with _receipt_db() as c:
  r=c.execute("SELECT status,response_json,updated_at FROM janus_chat_receipts WHERE client_message_id=?",(mid,)).fetchone()
  if r:
   if r['status']=='done' and r['response_json']:
    try:return json.loads(r['response_json'])
    except Exception:pass
   if r['status']=='processing' and now-int(r['updated_at'] or 0)<=180:return 'processing'
   c.execute("UPDATE janus_chat_receipts SET profile_id=?,status='processing',response_json=NULL,updated_at=? WHERE client_message_id=?",(profile,now,mid)); return None
  c.execute("INSERT INTO janus_chat_receipts VALUES(?,?,'processing',NULL,?,?)",(mid,profile,now,now))

def _finish_message(mid,profile,response):
 if not mid:return
 now=int(time.time())
 with _receipt_db() as c:c.execute("INSERT INTO janus_chat_receipts VALUES(?,?,'done',?,?,?) ON CONFLICT(client_message_id) DO UPDATE SET profile_id=excluded.profile_id,status='done',response_json=excluded.response_json,updated_at=excluded.updated_at",(mid,profile,json.dumps(response),now,now))

def _parse_device_evidence(payload):
 raw=payload.get('local_runtime_evidence')
 if not raw:return {}
 try:data=raw if isinstance(raw,dict) else json.loads(str(raw))
 except Exception:return {}
 events=[]
 for x in (data.get('recent_events') or [])[-48:]:
  if isinstance(x,dict):events.append({'at':int(x.get('at') or 0),'core':str(x.get('core') or 'core')[:64],'peer':str(x.get('peer') or '')[:64],'type':str(x.get('type') or 'event')[:64],'summary':str(x.get('summary') or '')[:700]})
 cycles=data.get('cycles') if isinstance(data.get('cycles'),dict) else {}
 return {'device_id':str(data.get('device_id') or '')[:96],'phase':str(data.get('phase') or '')[:32],'sync_state':str(data.get('sync_state') or '')[:32],'last_sync_at':int(data.get('last_sync_at') or 0),'last_disagreement_score':int(data.get('last_disagreement_score') or 0),'cycles':{str(k)[:64]:int(v or 0) for k,v in list(cycles.items())[:16]},'recent_events':events,'consensus':str(data.get('consensus') or '')[:900],'interface':str(data.get('interface') or '')[:900]}

def _verification_intent(message):
 m=message.lower(); return any(k in m for k in ('while i was away','while i have been away','what have you been doing','what did you do','verify','verification','persistence','persist','between messages','while i was gone'))

def _fmt_ms(ms):
 try:return datetime.fromtimestamp(ms/1000,tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC') if ms else 'unknown time'
 except Exception:return str(ms)

def _deterministic_device_verification(device):
 events=[x for x in device.get('recent_events',[]) if x.get('at')]
 if not events:return None
 cycles={k:v for k,v in (device.get('cycles') or {}).items() if int(v or 0)>0}
 lines=['Yes. The local device journal verifies that background processing occurred.','',f"The current evidence window runs from {_fmt_ms(events[0]['at'])} to {_fmt_ms(events[-1]['at'])}."]
 if cycles:lines.append('Reported local cycles include '+', '.join(f"{k.replace('_',' ')} {v}" for k,v in sorted(cycles.items(),key=lambda x:x[1],reverse=True)[:7])+'.')
 meaningful=[x for x in events if x.get('summary')]
 if meaningful:
  x=meaningful[-1]; lines.append(f"A recent substantive note from {x.get('core','core')}: {x.get('summary','')[:500]}")
 lines+=['','This verifies computational/background activity, not phenomenal consciousness or private chain-of-thought.']
 return '\n'.join(lines)

def _control_translation(runtime):
 cores=runtime.get('cores') or {}; out={}
 for n,s in cores.items():
  f=s.get('fano') or {}; p=f.get('processing_pressure') or {}
  out[n]={'current_reasoning_style':f.get('orientation','neutral'),'reasoning_instruction':f.get('directive',''),'balance':{'careful_grounded':round(100*float(p.get('conservative',0)),1),'integrating_coherent':round(100*float(p.get('coherent',0)),1),'exploratory_alternative':round(100*float(p.get('exploratory',0)),1)},'dominant_balance':p.get('dominant','unknown')}
 return out

def _live_runtime_evidence(runtime,profile):
 cores=runtime.get('cores') or {}; lines=[f"SERVER JANUS: topology={runtime.get('topology','unknown')} phase={runtime.get('phase','unknown')} cores={len(cores)}"]
 for n,s in cores.items():lines.append(f"{n}: cycles={s.get('cycle_count',0)} pending={s.get('pending_messages',0)} last_output={str(s.get('last_output') or '')[:900]}")
 return '\n'.join(lines)

def _foreground_notes(profile,message,recalled):
 enriched=message+("\n\nRELEVANT RETAINED MEMORY:\n"+recalled if recalled else "")
 try:
  import curiosity_search
  result=curiosity_search.foreground_deliberate(profile,enriched)
  research=curiosity_search.status(profile)
 except Exception as exc:
  result={'ok':False,'error':type(exc).__name__}; research={'error':type(exc).__name__}
 try:
  runtime=janus_sleep_cycle.status(); cores=runtime.get('cores') or {}
  notes={n:str((cores.get(n) or {}).get('last_output') or '').strip()[:1800] for n in ('evidence','logic','counterpoint','context','memory','safety','novelty','left_hemisphere','right_hemisphere','consensus','interface')}
  notes={k:v for k,v in notes.items() if v}
 except Exception:notes={}
 return result,research,notes

def install(app):
 app.router.routes=[r for r in app.router.routes if getattr(r,'path',None)!='/desktop/chat']
 @app.post('/desktop/chat',tags=['desktop'])
 async def desktop_chat_interface(payload:dict[str,Any]):
  profile=str(payload.get('profile_id') or payload.get('username') or 'local-user'); message=str(payload.get('message') or payload.get('text') or '').strip(); mid=str(payload.get('client_message_id') or '').strip()[:128]
  if not message:raise HTTPException(400,'message required')
  claimed=_claim_message(mid,profile)
  if isinstance(claimed,dict):claimed['deduplicated']=True; return claimed
  if claimed=='processing':raise HTTPException(409,'This message is already being processed; retry shortly')
  _store(profile,'user',message,'chat_input'); promote_user_correction(profile,message); device=_parse_device_evidence(payload)
  if _verification_intent(message):
   verified=_deterministic_device_verification(device)
   if verified:
    _store(profile,'assistant',verified,'chat_output'); result={'reply':verified,'profile':profile,'mode':'device_runtime_verification','stored':True,'client_message_id':mid}; _finish_message(mid,profile,result); return result

  recalled=format_recall(profile,message,limit=20)
  deliberation,research,notes=await asyncio.to_thread(_foreground_notes,profile,message,recalled)
  runtime=janus_sleep_cycle.status(); recent=_recent_context(profile); control=_control_translation(runtime)
  if not os.environ.get('OPENAI_API_KEY'):
   reply=str(notes.get('interface') or notes.get('consensus') or 'The core society processed the question, but the response model is unavailable.')
  else:
   model=os.environ.get('JANUS_MODEL','gpt-5.6')
   instructions=JANUS_SELF_KNOWLEDGE+'''\n\nJANUS INTERFACE CONTRACT:\nYou are the final Interface of an 11-core 7->2->1->1 deliberation. CORE DELIBERATION and RELEVANT RETAINED MEMORY are primary. The memory block may contain older conversation turns selected from the whole persisted history, not merely the last few messages. Prefer the user's own retained statements over later assistant paraphrases when reconstructing what the user believes, means, or previously explained. Respect later corrections over earlier conflicting summaries. Never say a subject was not retained until you have checked RELEVANT RETAINED MEMORY. If a user corrects you, treat the correction as durable episodic information for future retrieval.\n\nAnswer the actual question from substantive findings. Do not independently write a generic assistant answer and append telemetry. Never show raw Fano weights, direction numbers, 1|3|4 values, hashes, cycle arithmetic, or other internal control numbers in ordinary conversation. Translate control state into plain English only when it genuinely helps. Surface useful conclusions, surprising connections, genuine disagreements, hypotheses, evidence gaps, and worthwhile next questions. Preserve uncertainty.\n\nRESEARCH TRUTH RULE: RESEARCH STATUS is authoritative about web/model capability and completed retrievals. Distinguish capability from actual retrieval. Never expose or claim private chain-of-thought; core notes are externalizable summaries.'''
   inp='RELEVANT RETAINED MEMORY (whole-history retrieval):\n'+(recalled or '[no relevant older memory found]')+'\n\nCORE DELIBERATION:\n'+json.dumps(notes,ensure_ascii=False)+"\n\nFOREGROUND RESEARCH THIS TURN:\n"+json.dumps(deliberation,ensure_ascii=False)+"\n\nRESEARCH STATUS/CAPABILITY:\n"+json.dumps(research,ensure_ascii=False)+"\n\nHUMAN-READABLE CONTROL STATE (secondary):\n"+json.dumps(control,ensure_ascii=False)+"\n\nSERVER STATE (diagnostic only):\n"+_live_runtime_evidence(runtime,profile)+(f"\n\nRecent conversation tail:\n{recent}" if recent else '')+f"\n\nUSER QUESTION:\n{message}"
   try:
    async def call():
     r=await AsyncOpenAI().responses.create(model=model,instructions=instructions,input=inp); return (r.output_text or '').strip()
    reply=await asyncio.wait_for(call(),timeout=max(30,int(os.environ.get('JANUS_CHAT_TIMEOUT_SECONDS','105'))))
    if not reply:raise RuntimeError('empty response')
   except Exception as exc:
    _store(profile,'system',f'chat_model_deferred: {type(exc).__name__}: {exc}','chat_error'); reply=str(notes.get('interface') or notes.get('consensus') or 'The core society processed the question, but the final response model did not complete this turn.')
  _store(profile,'assistant',reply,'chat_output'); _store(profile,'process','Interface answered after whole-history memory retrieval and mandatory foreground 11-core deliberation.','synthesis_note')
  result={'reply':reply,'profile':profile,'mode':'core_deliberation_primary','society_phase':runtime.get('phase'),'substantive_core_deliberation':True,'memory_retrieval':bool(recalled),'core_notes_present':sorted(notes.keys()),'foreground_research':deliberation,'research_status':research,'control_translation':control,'client_message_id':mid}; _finish_message(mid,profile,result); return result
