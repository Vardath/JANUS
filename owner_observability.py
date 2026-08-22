"""Owner-facing JANUS observability: translate runtime telemetry into useful English."""
from __future__ import annotations
import os, sqlite3, time
from typing import Any
import cost_governor

DB_PATH=os.environ.get("JANUS_DB_PATH","/data/janus.sqlite3")

def _count(table:str, profile:str)->int:
    try:
        c=sqlite3.connect(DB_PATH)
        try:return int(c.execute(f"SELECT COUNT(*) FROM {table} WHERE profile_id=?",(profile,)).fetchone()[0])
        finally:c.close()
    except Exception:return 0

def _recent_failures(profile:str)->list[dict[str,Any]]:
    try:
        c=sqlite3.connect(DB_PATH); c.row_factory=sqlite3.Row
        try:
            rows=c.execute("SELECT capability,status,detail,created_at FROM janus_cost_events WHERE profile_id=? AND status NOT IN ('complete','cancelled') ORDER BY id DESC LIMIT 5",(profile,)).fetchall()
            return [dict(r) for r in rows]
        finally:c.close()
    except Exception:return []

def snapshot(profile:str,runtime:dict[str,Any])->dict[str,Any]:
    cost=cost_governor.status(profile); failures=_recent_failures(profile)
    thread=bool(runtime.get('server_runtime_thread_alive')); online=int(runtime.get('remote_clients') or 0); registered=int(runtime.get('registered_clients') or 0)
    degraded=[]
    if not thread: degraded.append('The server background core cycle is not running.')
    if registered and not online: degraded.append('Registered local devices are currently offline; server continuity remains available.')
    if failures: degraded.append(f"{len(failures)} recent external-provider failure(s) were recorded; JANUS should degrade rather than stop.")
    if cost.get('denied_today'): degraded.append(f"{cost['denied_today']} external-compute request(s) were denied by budget protection today.")
    state='healthy' if not degraded else ('degraded' if thread else 'attention')
    summary=(
        'JANUS server and local presence look healthy.' if state=='healthy' else
        'JANUS is operating with reduced capability; core continuity is preserved.' if state=='degraded' else
        'JANUS needs attention because the server background cycle is not confirmed running.'
    )
    return {
      'profile':profile,'state':state,'summary':summary,'needs_attention':bool(degraded),'explanations':degraded,
      'server':{'background_cycle_running':thread,'phase':runtime.get('phase') or 'unknown','core_cycle_external_api_calls':0},
      'local_devices':{'online':online,'registered':registered,'presence':runtime.get('presence_state') or 'unknown','latest_device':runtime.get('latest_remote_device_id') or None,'latest_client_version':runtime.get('latest_remote_client_version') or None},
      'costs':cost,'provider_failures':failures,
      'continuity':{'memory_records':_count('desktop_memory',profile),'message_events':_count('desktop_events',profile)},
      'policy':{'background_work_degrades_before_foreground_chat':True,'failed_provider_calls_do_not_consume_estimated_budget':True,'local_and_server_state_are_reported_separately':True},
      'generated_at':int(time.time())
    }

def install(app,runtime_fn):
    paths={getattr(r,'path','') for r in app.router.routes}
    if '/desktop/owner-status' in paths:return
    @app.get('/desktop/owner-status',tags=['desktop'])
    def owner_status(username:str):
        return snapshot(username,runtime_fn(username))
