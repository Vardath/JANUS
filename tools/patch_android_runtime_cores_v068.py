from pathlib import Path
import re

runtime = Path('android/app/src/main/java/com/vardath/janus/JanusLocalCoreRuntime.java')
r = runtime.read_text(encoding='utf-8')

# One consolidated native server-snapshot path. No older telemetry patch is required.
if 'private volatile String lastServerStatus=' not in r:
    r = r.replace('private final String installationId;', 'private final String installationId;\n    private volatile String lastServerStatus="";')
if 'lastServerStatus=prefs.getString("core_server_status","")' not in r:
    r = r.replace('lastSyncAt=prefs.getLong("core_last_sync_at",0L);', 'lastSyncAt=prefs.getLong("core_last_sync_at",0L); lastServerStatus=prefs.getString("core_server_status","");')
if 'synchronized String serverStatusJson()' not in r:
    r = r.replace('private JSONObject summary() throws Exception', 'synchronized String serverStatusJson(){return lastServerStatus==null?"":lastServerStatus;}\n\n    private JSONObject summary() throws Exception')

pat = r'JSONObject\s+server\s*=\s*new\s+JSONObject\(b\.toString\(\)\)\.optJSONObject\("server"\);'
m = re.search(pat, r)
if not m:
    raise SystemExit('v0.69: core-sync server parse point not found')
cap = 'if(server!=null){lastServerStatus=server.toString();prefs.edit().putString("core_server_status",lastServerStatus).apply();}'
if cap not in r:
    r = r[:m.end()] + cap + r[m.end():]
r = re.sub(r'("client_version"\s*,\s*")0\.(?:[0-9]+)("\s*\))', r'\g<1>0.69\2', r)
runtime.write_text(r, encoding='utf-8')

activity = Path('android/app/src/main/java/com/vardath/janus/MainActivity.java')
a = activity.read_text(encoding='utf-8')
if '@JavascriptInterface public String serverCoreStatus()' not in a:
    marker = '@JavascriptInterface public void googleSignIn()'
    if marker not in a:
        raise SystemExit('v0.69: MainActivity bridge marker missing')
    a = a.replace(marker, '@JavascriptInterface public String serverCoreStatus() { try { return JanusLocalCoreRuntime.get(MainActivity.this).serverStatusJson(); } catch (Exception e) { return ""; } }\n        ' + marker, 1)

# Override Cores rendering at the final Java injection point so no older web logic can replace it.
if '__janusTelemetryV068' not in a:
    marker = 'view.evaluateJavascript(js, null);'
    if marker not in a:
        raise SystemExit('v0.69: evaluateJavascript marker missing')
    override = '''js += "window.__janusTelemetryV068=true;window.refreshCoreTopology=function(){var host=document.getElementById('coreTopology');if(!host)return;var local={};try{local=JSON.parse(Android.localCoreStatus()||'{}');}catch(e){}var raw='';try{raw=Android.serverCoreStatus()||'';}catch(e){}var server={};try{if(raw)server=JSON.parse(raw);}catch(e){}var has=server&&server.cores&&Object.keys(server.cores).length>0;var intro='<div class=\\\"card\\\"><b>JANUS 11-core topology</b><div class=\\\"small\\\">This device and Server JANUS are independent runtimes. Server values come from the authenticated core-sync exchange already used by this app.</div></div>';var sh=has?window.renderCoreSide('SERVER JANUS · LIVE',server,false):'<div class=\\\"card\\\"><b>SERVER JANUS · WAITING FOR SYNC SNAPSHOT</b><div class=\\\"small\\\">Local sync: '+esc(local.sync_state||'unknown')+'. Snapshot bytes: '+esc(raw?raw.length:0)+'. Connected + zero bytes means native capture failed; nonzero bytes means rendering/parser failed.</div></div>';host.innerHTML=intro+window.renderCoreSide('THIS DEVICE JANUS · LIVE',local,true)+sh;};if(!window.__janusTelemetryPollV068){window.__janusTelemetryPollV068=setInterval(function(){try{var v=document.getElementById('cores');if(v&&v.classList.contains('active'))window.refreshCoreTopology();}catch(e){}},3000);}";\n                '''
    a = a.replace(marker, override + marker, 1)
activity.write_text(a, encoding='utf-8')

html = Path('android/app/src/main/assets/index.html')
h = html.read_text(encoding='utf-8')

# Give the server Interface concrete retained subject matter with every user turn.
needle = "let ev=(r.observe_events||[]).slice(-48).map(x=>({at:x.created_at,core:x.core_name,peer:x.peer_core||'',type:x.event_type,summary:x.detail||''}));return JSON.stringify"
if needle in h and 'memory_context' not in h:
    repl = "let ev=(r.observe_events||[]).slice(-36).map(x=>({at:x.created_at,core:x.core_name,peer:x.peer_core||'',type:x.event_type,summary:x.detail||''}));let mem=(r.local_memories||[]).slice(-12);mem.forEach(function(m){ev.push({at:0,core:'memory',peer:'',type:'memory_context',summary:String(m).slice(0,700)});});return JSON.stringify"
    h = h.replace(needle, repl, 1)

# Phase 2 Step 9: show owner-facing observability inside Android Options in plain English.
all_old = "const main=['chat','messages','observe','options'],all=[...main,'cores','memory','activity','settings'];"
all_new = "const main=['chat','messages','observe','options'],all=[...main,'cores','memory','activity','ownerstatus','settings'];"
if all_old in h:
    h = h.replace(all_old, all_new, 1)

activity_btn = '<button onclick="showSub(\'activity\')"><b>Activity</b><br><span class="small">Conversation, reflections, decisions and events</span></button>'
status_btn = activity_btn + '<button onclick="show(\'ownerstatus\');refreshOwnerStatus()"><b>System status</b><br><span class="small">Server, local sync, memory, costs and provider health in plain English</span></button>'
if activity_btn in h and 'refreshOwnerStatus()' not in h:
    h = h.replace(activity_btn, status_btn, 1)

settings_view = '<div id="settings" class="view"><button class="action secondary" onclick="show(\'options\')">← Options</button><h2>Settings</h2>'
owner_view = '<div id="ownerstatus" class="view"><button class="action secondary" onclick="show(\'options\')">← Options</button><h2>System Status</h2><p class="small">A plain-English diagnostic view. Server and this device are reported separately.</p><button class="action secondary" onclick="refreshOwnerStatus()">Refresh status</button><div id="ownerStatusList"><div class="card">Loading JANUS status…</div></div></div>\n' + settings_view
if settings_view in h and 'id="ownerstatus"' not in h:
    h = h.replace(settings_view, owner_view, 1)

status_js = r'''
async function refreshOwnerStatus(){
  let host=document.getElementById('ownerStatusList');if(!host)return;
  host.innerHTML='<div class="card">Refreshing JANUS status…</div>';
  try{
    let r=await api('GET','/desktop/owner-status?username='+encodeURIComponent(profile));
    let local={};try{local=JSON.parse(Android.localCoreStatus()||'{}')}catch(e){}
    let state=String(r.state||'unknown'), explanations=Array.isArray(r.explanations)?r.explanations:[];
    let server=r.server||{}, devices=r.local_devices||{}, continuity=r.continuity||{}, costs=r.costs||{};
    let stateText=state==='healthy'?'Healthy':state==='degraded'?'Reduced capability':state==='attention'?'Needs attention':'Status unknown';
    let h='<div class="card"><b>'+esc(stateText)+'</b><p>'+esc(r.summary||'JANUS status is available below.')+'</p>';
    if(explanations.length)h+='<ul>'+explanations.map(x=>'<li>'+esc(x)+'</li>').join('')+'</ul>';h+='</div>';
    h+='<div class="card"><b>Server JANUS</b><p>'+(server.background_cycle_running?'The global background core cycle is running.':'The global background core cycle is not confirmed running.')+'</p><div class="small">Phase: '+esc(server.phase||'unknown')+' · autonomous core-cycle API calls: '+esc(server.core_cycle_external_api_calls||0)+'</div></div>';
    h+='<div class="card"><b>This device and synchronization</b><p>'+(devices.online>0?'This device/account currently has an authenticated local client online.':devices.registered>0?'A local device is registered but currently offline. Server continuity can continue without it.':'No authenticated local device heartbeat is currently registered.')+'</p><div class="small">Online '+esc(devices.online||0)+' · registered '+esc(devices.registered||0)+' · sync '+esc(devices.presence||local.sync_state||'unknown')+'</div></div>';
    h+='<div class="card"><b>Memory and continuity</b><p>JANUS has '+esc(continuity.memory_records||0)+' retained memory record(s) and '+esc(continuity.message_events||0)+' recorded conversation/activity event(s) for this profile.</p><div class="small">These are persisted records, not hidden chain-of-thought.</div></div>';
    let spent=(costs.spent_today_usd!==undefined?costs.spent_today_usd:costs.estimated_spend_today_usd);let denied=costs.denied_today||0;
    h+='<div class="card"><b>External-compute budget</b><p>'+(denied?esc(denied)+' optional external-compute request(s) have been blocked by budget protection today.':'No budget-protection blocks are currently reported today.')+'</p>'+(spent!==undefined?'<div class="small">Estimated successful external spend today: $'+esc(Number(spent||0).toFixed(4))+'</div>':'')+'</div>';
    let failures=Array.isArray(r.provider_failures)?r.provider_failures:[];
    h+='<div class="card"><b>Provider health</b><p>'+(failures.length?esc(failures.length)+' recent provider failure(s) are recorded. JANUS is configured to degrade rather than stop.':'No recent external-provider failures are reported.')+'</p>'+(failures.length?'<div class="small">'+failures.slice(0,3).map(x=>esc((x.capability||'provider')+': '+(x.status||'error'))).join('<br>')+'</div>':'')+'</div>';
    host.innerHTML=h;
  }catch(e){
    let local={};try{local=JSON.parse(Android.localCoreStatus()||'{}')}catch(_){}
    host.innerHTML='<div class="card"><b>Server status unavailable</b><p>The app could not retrieve the authenticated server diagnostic right now.</p><div class="small">Local JANUS: '+esc(local.phase||'unknown')+' · sync '+esc(local.sync_state||'unknown')+'. Local operation may continue independently.</div></div>';
  }
}
'''
if 'async function refreshOwnerStatus()' not in h:
    close='</script>'
    if close not in h:
        raise SystemExit('v0.69: HTML script close marker missing')
    h=h.replace(close,status_js+'\n'+close,1)

for v in ('0.59','0.60','0.61','0.62','0.63','0.64','0.65','0.66','0.67','0.68'):
    h = h.replace(f'LIVE LOCAL JANUS · v{v}', 'LIVE LOCAL JANUS · v0.69')
    h = h.replace(f"client_version:'{v}'", "client_version:'0.69'")
html.write_text(h, encoding='utf-8')
print('Android v0.69: consolidated telemetry + owner-facing system status')