from pathlib import Path

runtime = Path('android/app/src/main/java/com/vardath/janus/JanusLocalCoreRuntime.java')
r = runtime.read_text(encoding='utf-8')

# Keep the last full server status returned by the already-working authenticated
# /core-sync/exchange heartbeat. This removes the second WebView HTTP path entirely.
if 'lastServerStatus' not in r:
    r = r.replace(
        'private final String installationId;',
        'private final String installationId;\n    private volatile String lastServerStatus="";'
    )

if 'core_server_status' not in r:
    r = r.replace(
        'lastSyncAt=prefs.getLong("core_last_sync_at",0L);',
        'lastSyncAt=prefs.getLong("core_last_sync_at",0L); lastServerStatus=prefs.getString("core_server_status","");'
    )

# Persist every authoritative server snapshot that arrives on heartbeat.
needle = 'JSONObject server=envelope.optJSONObject("server");'
if needle in r and 'lastServerStatus=server.toString()' not in r:
    r = r.replace(
        needle,
        needle + 'if(server!=null){lastServerStatus=server.toString();prefs.edit().putString("core_server_status",lastServerStatus).apply();}'
    )

# Native bridge getter used by the WebView. No network call happens here.
if 'serverStatusJson()' not in r:
    marker = 'private JSONObject summary() throws Exception'
    if marker not in r:
        raise SystemExit('summary marker missing')
    r = r.replace(marker, 'synchronized String serverStatusJson(){return lastServerStatus==null?"":lastServerStatus;}\n\n    ' + marker)

# Truthful client version in the heartbeat payload after prior patches run.
r = r.replace('"client_version","0.63"', '"client_version","0.64"')
r = r.replace('"client_version","0.62"', '"client_version","0.64"')
runtime.write_text(r, encoding='utf-8')

activity = Path('android/app/src/main/java/com/vardath/janus/MainActivity.java')
a = activity.read_text(encoding='utf-8')

if '@JavascriptInterface public String serverCoreStatus()' not in a:
    marker = '@JavascriptInterface public void googleSignIn()'
    if marker not in a:
        raise SystemExit('Bridge googleSignIn marker missing')
    a = a.replace(
        marker,
        '@JavascriptInterface public String serverCoreStatus() { try { return JanusLocalCoreRuntime.get(MainActivity.this).serverStatusJson(); } catch (Exception e) { return ""; } }\n        ' + marker
    )

# Override every older topology implementation at the very end of onPageFinished.
# Server data comes from the exact heartbeat that already proves connected in the
# local diagnostic. Empty data is shown honestly as waiting, never as fake zeros.
if '__janusHeartbeatTopologyV064' not in a:
    marker = 'view.evaluateJavascript(js, null);'
    if marker not in a:
        raise SystemExit('evaluateJavascript marker missing')
    override = '''js += "window.__janusHeartbeatTopologyV064=true;window.refreshCoreTopology=async function(){var host=document.getElementById('coreTopology');if(!host)return;var local={};try{local=JSON.parse(Android.localCoreStatus()||'{}');}catch(e){}var raw='';try{raw=Android.serverCoreStatus()||'';}catch(e){}var server={};if(raw){try{server=JSON.parse(raw);}catch(e){server={};}}var hasServer=server&&server.cores&&Object.keys(server.cores).length>0;var intro='<div class=\\\"card\\\"><b>JANUS 11-core topology</b><p><b>Two independent runtimes.</b> This device is local. Server JANUS is the persistent Render society.</p><div class=\\\"small\\\">Server values below come from the authenticated heartbeat already used for synchronization; no second web request is involved.</div></div>';var sh=hasServer?window.renderCoreSide('SERVER JANUS · LIVE',server,false):'<div class=\\\"card\\\"><b>SERVER JANUS · WAITING FOR HEARTBEAT</b><div class=\\\"small\\\">No full server snapshot has been received by this app yet. Local sync state: '+esc(local.sync_state||'unknown')+'. This panel will update after the next authenticated heartbeat.</div></div>';host.innerHTML=intro+window.renderCoreSide('THIS DEVICE JANUS · LIVE',local,true)+sh;};";\n                '''
    a = a.replace(marker, override + marker, 1)

# Truthful visible version labels if older patch text remains in generated UI.
for v in ('0.60','0.61','0.62','0.63'):
    a = a.replace(f'LIVE LOCAL JANUS · v{v}', 'LIVE LOCAL JANUS · v0.64')
activity.write_text(a, encoding='utf-8')

html = Path('android/app/src/main/assets/index.html')
h = html.read_text(encoding='utf-8')
for v in ('0.59','0.60','0.61','0.62','0.63'):
    h = h.replace(f'LIVE LOCAL JANUS · v{v}', 'LIVE LOCAL JANUS · v0.64')
    h = h.replace(f"client_version:'{v}'", "client_version:'0.64'")
html.write_text(h, encoding='utf-8')

print('Patched Android v0.64: server Cores panel is driven by authenticated heartbeat snapshot')
