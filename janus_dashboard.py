"""JANUS dashboard extensions: persistent proactive outbox over the global core."""
from __future__ import annotations
import json, os, sqlite3
from datetime import datetime, timezone
from typing import Any
from fastapi import HTTPException, Query
from dashboard_api import app
from runtime_messaging import install as install_runtime_messaging
from secure_desktop import install as install_secure_desktop
from retention import install as install_retention
from auth import router as auth_router, google_auth as current_google_auth, GoogleRequest
from account_deletion import router as account_deletion_router
from privacy_policy import router as privacy_policy_router
from terms_of_service import router as terms_router
from ai_reports import router as ai_reports_router
from core_sync import router as core_sync_router
from src.janus_sleep_cycle import janus_sleep_cycle
from interface_runtime_policy import install as install_interface_runtime_policy
from interface_chat import install as install_interface_chat
from deliberation_tasks import install as install_deliberation_tasks
from curiosity_search import install as install_curiosity_search
from epistemic_search_bridge import install as install_epistemic_search_bridge
from core_observer import install as install_core_observer
from autonomous_hive import install as install_autonomous_hive
from self_assessment import install as install_self_assessment
from server_low_duty import install as install_server_low_duty
from routing_policy import install as install_routing_policy

DB_PATH = os.environ.get("JANUS_DB_PATH", "/data/janus.sqlite3")
# The autonomous hive owns background cognition now. Keep the older dashboard
# reflection loop off unless explicitly re-enabled, avoiding duplicate paid calls.
os.environ.setdefault("JANUS_SELF_EVALUATION", "0")
janus_sleep_cycle.wake_seconds = max(10, int(os.environ.get("JANUS_WAKE_SECONDS", "300")))
janus_sleep_cycle.sleep_seconds = max(10, int(os.environ.get("JANUS_SLEEP_SECONDS", "600")))
install_interface_runtime_policy(janus_sleep_cycle)
install_server_low_duty(janus_sleep_cycle)
install_routing_policy(janus_sleep_cycle)
install_core_observer(app, janus_sleep_cycle)
install_autonomous_hive(app)
install_self_assessment(app)

def _connect():
    c=sqlite3.connect(DB_PATH,timeout=10); c.row_factory=sqlite3.Row
    c.execute("CREATE TABLE IF NOT EXISTS janus_message_state (profile_id TEXT NOT NULL,event_id INTEGER NOT NULL,state TEXT NOT NULL DEFAULT 'unread',PRIMARY KEY(profile_id,event_id))"); c.commit(); return c

def _message_type(event_type:str,detail:str)->str:
    text=(detail or '').lower()
    if '?' in (detail or '') or event_type=='question': return 'Question'
    if 'memory' in text or 'remember' in text: return 'Memory'
    if 'reflection' in text or 'noticed' in text: return 'Observation'
    return 'Follow-up'

def _decode_message(event_type:str,detail:str):
    raw=str(detail or '')
    if event_type=='proactive_message':
        try:
            p=json.loads(raw)
            if isinstance(p,dict) and str(p.get('text') or '').strip(): return str(p.get('message_type') or 'Follow-up'),str(p.get('text')).strip(),str(p.get('source') or 'janus')
        except Exception: pass
    return _message_type(event_type,raw),'legacy' if False else raw,'legacy'

def _message_rows(profile:str,limit:int=50,include_dismissed:bool=False):
    c=_connect()
    try:
        rows=c.execute("SELECT e.id,e.event_type,e.detail,e.created_at,COALESCE(s.state,'unread') state FROM desktop_events e LEFT JOIN janus_message_state s ON s.profile_id=e.profile_id AND s.event_id=e.id WHERE e.profile_id=? AND e.event_type IN ('message_candidate','proactive_message','question') ORDER BY e.id DESC LIMIT ?",(profile,limit*2 if not include_dismissed else limit)).fetchall(); items=[]
        for row in rows:
            item=dict(row)
            if not include_dismissed and item['state']=='dismissed': continue
            mt,text,source=_decode_message(item['event_type'],item['detail']); item.update(message_type=mt,detail=text,source=source); items.append(item)
            if len(items)>=limit: break
        return items
    finally: c.close()

def _presence(profile,latest):
    runtime=janus_sleep_cycle.status()
    if runtime.get('interface_awake'): return 'Active'
    if runtime.get('interface_available'): return 'Active'
    if runtime.get('phase')=='wake': return 'Active'
    if not latest or not latest.get('created_at'): return 'Dormant'
    try:
        stamp=datetime.fromisoformat(str(latest['created_at']).replace('Z','+00:00')); age=(datetime.now(timezone.utc)-stamp.astimezone(timezone.utc)).total_seconds(); interval=max(1,int(os.environ.get('JANUS_INTERVAL_MINUTES','15')))*60
        return 'Active' if age<=interval*2 else 'Dormant'
    except Exception: return 'Dormant'

@app.on_event('startup')
async def _start_local_core_cycle(): janus_sleep_cycle.start()
@app.on_event('shutdown')
async def _stop_local_core_cycle(): janus_sleep_cycle.stop()

@app.get('/desktop/runtime-cores',tags=['desktop'])
def desktop_runtime_cores(username:str|None=Query(default=None)):
    runtime=janus_sleep_cycle.status()
    return {'profile':username or 'unspecified','architecture':'11-core: 7 specialists + 2 hemispheres + consensus + interface','runtime':runtime,'paid_background_api_enabled':os.environ.get('JANUS_PAID_BACKGROUND_REFLECTION','1')=='1','curiosity_web_enabled':os.environ.get('JANUS_CURIOSITY_WEB','1')=='1','curiosity_daily_search_cap':int(os.environ.get('JANUS_CURIOSITY_DAILY_SEARCH_CAP','4')),'hive_pulse_seconds':int(os.environ.get('JANUS_HIVE_PULSE_SECONDS','60')),'paid_reflection_seconds':int(os.environ.get('JANUS_BACKGROUND_REFLECTION_SECONDS','1800')),'self_assess_seconds':int(os.environ.get('JANUS_SELF_ASSESS_SECONDS','300')),'background_model':os.environ.get('JANUS_BACKGROUND_MODEL','gpt-5.6-luna'),'rest_background_seconds':runtime.get('rest_background_seconds',30),'core_cycle_api_calls':0,'note':'The interface remains continuously available. Local/server core cycles are deterministic and zero-API; occasional bounded web curiosity is separate, inspectable, cached in memory, and budget-capped. Self-assessment may temporarily rebalance work toward fresh grounding and request a bounded relevant search when epistemic productivity falls.'}

@app.get('/desktop/messages',tags=['desktop'])
def desktop_messages(username:str=Query(...),limit:int=Query(default=50,ge=1,le=100),include_dismissed:bool=Query(default=False)):
    items=_message_rows(username,limit,include_dismissed); return {'profile':username,'items':items,'unread':sum(1 for x in items if x['state']=='unread'),'message_types':['Question','Observation','Memory','Follow-up'],'purpose':"JANUS's persistent outbox to the user.",'runtime_action':True}

@app.post('/desktop/messages/{event_id}/state',tags=['desktop'])
def desktop_message_state(event_id:int,payload:dict[str,Any]):
    profile=str(payload.get('profile_id') or payload.get('username') or '').strip(); state=str(payload.get('state') or 'read').strip().lower()
    if not profile: raise HTTPException(400,'profile_id required')
    if state not in {'unread','read','dismissed'}: raise HTTPException(400,'state must be unread, read or dismissed')
    c=_connect()
    try:
        if not c.execute('SELECT 1 FROM desktop_events WHERE id=? AND profile_id=?',(event_id,profile)).fetchone(): raise HTTPException(404,'message not found')
        c.execute("INSERT INTO janus_message_state(profile_id,event_id,state) VALUES(?,?,?) ON CONFLICT(profile_id,event_id) DO UPDATE SET state=excluded.state",(profile,event_id,state)); c.commit()
    finally: c.close()
    return {'ok':True,'event_id':event_id,'state':state}

@app.get('/desktop/home',tags=['desktop'])
def desktop_home(username:str=Query(...)):
    messages=_message_rows(username,50); c=_connect()
    try:
        row=c.execute('SELECT event_type,detail,created_at FROM desktop_events WHERE profile_id=? ORDER BY id DESC LIMIT 1',(username,)).fetchone(); latest=dict(row) if row else None
    finally: c.close()
    runtime=janus_sleep_cycle.status(); return {'profile':username,'status':_presence(username,latest),'architecture':'11-core','unread_messages':sum(1 for x in messages if x['state']=='unread'),'latest_activity':latest,'background_interval_minutes':1,'core_phase':runtime.get('phase'),'core_runtime':runtime,'external_api_budget_used_by_core_cycle':0,'messaging_action':True}

app.router.routes = [route for route in app.router.routes if getattr(route, 'path', None) != '/auth/google']

@app.post('/auth/google', tags=['auth'])
def google_auth_android_compat(req: GoogleRequest):
    result = current_google_auth(req)
    account = result.get('account') or {}
    username = str(account.get('username') or '').strip()
    account_id = account.get('id')
    result['username'] = username
    result['profile_id'] = username
    result['account_id'] = account_id
    result['user_id'] = account_id
    return result

app.include_router(auth_router); app.include_router(account_deletion_router); app.include_router(privacy_policy_router); app.include_router(terms_router); app.include_router(ai_reports_router); app.include_router(core_sync_router)
install_interface_chat(app)
install_deliberation_tasks(app)
install_curiosity_search(app)
install_epistemic_search_bridge(app)
install_runtime_messaging(app); install_secure_desktop(app); install_retention(app)