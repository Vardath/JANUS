from pathlib import Path

runtime = Path('android/app/src/main/java/com/vardath/janus/JanusLocalCoreRuntime.java')
s = runtime.read_text(encoding='utf-8')
s = s.replace('"client_version","0.56"', '"client_version","0.57"')

old_reply = '''        cores.get("memory").inbox.addLast("server response to retain: "+clean);\n        cores.get("context").inbox.addLast("server response context: "+clean);\n        cores.get("counterpoint").inbox.addLast("review server response for unresolved alternatives: "+clean);'''
new_reply = '''        for(String n:SPECIALISTS) cores.get(n).inbox.addLast("server-response-grounding: "+clean);'''
if old_reply in s:
    s = s.replace(old_reply, new_reply)

old_grounding = '''cores.get("evidence").inbox.addLast(tagged);cores.get("context").inbox.addLast(tagged);cores.get("memory").inbox.addLast(tagged);cores.get("counterpoint").inbox.addLast(tagged);'''
if old_grounding in s:
    s = s.replace(old_grounding, 'for(String target:SPECIALISTS)cores.get(target).inbox.addLast(tagged);')

marker = 'synchronized void clearAccessToken(){accessToken="";prefs.edit().remove("access_token").apply();lastSyncState="not-signed-in";}'
if marker not in s:
    raise SystemExit('clearAccessToken marker not found after global connectivity patch')
if 'markGlobalHeartbeat' not in s:
    s = s.replace(marker, marker + '\n    synchronized void markGlobalHeartbeat(boolean connected,String detail){lastSyncState=connected?"connected":"reachable-auth-pending";if(connected)lastSyncAt=System.currentTimeMillis();record("interface",null,"maintenance",connected?"Authenticated global heartbeat confirmed.":"Global server reachable but authenticated heartbeat not confirmed: "+clip(detail,240));persist();}')
runtime.write_text(s, encoding='utf-8')

activity = Path('android/app/src/main/java/com/vardath/janus/MainActivity.java')
a = activity.read_text(encoding='utf-8')
bridge_marker = '''        @JavascriptInterface public String localCoreStatus() {\n            try { return JanusLocalCoreRuntime.get(MainActivity.this).statusJson().toString(); }\n            catch (Exception e) { return "{\\\"architecture\\\":\\\"11-core\\\",\\\"phase\\\":\\\"unknown\\\",\\\"error\\\":\\\"local status unavailable\\\"}"; }\n        }'''
if bridge_marker not in a:
    raise SystemExit('localCoreStatus bridge marker not found')
if 'globalHeartbeatResult' not in a:
    a = a.replace(bridge_marker, bridge_marker + '\n        @JavascriptInterface public void globalHeartbeatResult(boolean connected, String detail) { JanusLocalCoreRuntime.get(MainActivity.this).markGlobalHeartbeat(connected, detail); }')
activity.write_text(a, encoding='utf-8')

html = Path('android/app/src/main/assets/index.html')
h = html.read_text(encoding='utf-8')
insert = '''\nasync function janusAuthenticatedHeartbeat(){if(!profile||!token)return;try{let r=JSON.parse(Android.localCoreStatus()||'{}'),cs=r.cores||{},cycles={};Object.keys(cs).forEach(k=>cycles[k]=Number(cs[k].cycle_count||0));let payload={device_id:r.installation_id||('android-'+String(accountId||profile||'device')),platform:'android',client_version:'0.57',phase:r.phase||'unknown',consensus:String(r.consensus||'').slice(0,1000),interface:String(r.interface||'').slice(0,1000),cycles:cycles,observe_events:[],memories:[],conclusions:[]};let x=await api('POST','/core-sync/exchange',payload);Android.globalHeartbeatResult(true,'online '+String((x.presence&&x.presence.online)||0));}catch(e){try{Android.globalHeartbeatResult(false,String(e&&e.message||e||'heartbeat failed'));}catch(_){}}}\nsetInterval(janusAuthenticatedHeartbeat,15000);setTimeout(janusAuthenticatedHeartbeat,1200);\n'''
anchor = 'loadSettings();if(token&&localStorage.janusProfile)'
if anchor not in h:
    raise SystemExit('index bootstrap anchor not found')
if 'janusAuthenticatedHeartbeat' not in h:
    h = h.replace(anchor, insert + anchor)
html.write_text(h, encoding='utf-8')
print('Patched Android v0.57 authenticated WebView heartbeat + authoritative sync state + balanced seven-specialist review')
