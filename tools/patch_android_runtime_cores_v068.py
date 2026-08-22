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
    raise SystemExit('v0.68: core-sync server parse point not found')
cap = 'if(server!=null){lastServerStatus=server.toString();prefs.edit().putString("core_server_status",lastServerStatus).apply();}'
if cap not in r:
    r = r[:m.end()] + cap + r[m.end():]
r = re.sub(r'("client_version"\s*,\s*")0\.(?:[0-9]+)("\s*\))', r'\g<1>0.68\2', r)
runtime.write_text(r, encoding='utf-8')

activity = Path('android/app/src/main/java/com/vardath/janus/MainActivity.java')
a = activity.read_text(encoding='utf-8')
if '@JavascriptInterface public String serverCoreStatus()' not in a:
    marker = '@JavascriptInterface public void googleSignIn()'
    if marker not in a:
        raise SystemExit('v0.68: MainActivity bridge marker missing')
    a = a.replace(marker, '@JavascriptInterface public String serverCoreStatus() { try { return JanusLocalCoreRuntime.get(MainActivity.this).serverStatusJson(); } catch (Exception e) { return ""; } }\n        ' + marker, 1)

# Override Cores rendering at the final Java injection point so no older web logic can replace it.
if '__janusTelemetryV068' not in a:
    marker = 'view.evaluateJavascript(js, null);'
    if marker not in a:
        raise SystemExit('v0.68: evaluateJavascript marker missing')
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
for v in ('0.59','0.60','0.61','0.62','0.63','0.64','0.65','0.66','0.67'):
    h = h.replace(f'LIVE LOCAL JANUS · v{v}', 'LIVE LOCAL JANUS · v0.68')
    h = h.replace(f"client_version:'{v}'", "client_version:'0.68'")
html.write_text(h, encoding='utf-8')
print('Android v0.68 consolidated: one heartbeat snapshot path + concrete memory context')
