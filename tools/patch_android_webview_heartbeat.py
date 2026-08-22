from pathlib import Path

runtime = Path('android/app/src/main/java/com/vardath/janus/JanusLocalCoreRuntime.java')
s = runtime.read_text(encoding='utf-8')
s = s.replace('"client_version","0.56"', '"client_version","0.58"')
s = s.replace('"client_version","0.57"', '"client_version","0.58"')

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
insert = '''\nfunction janusLocalSnapshot(){try{return JSON.parse(Android.localCoreStatus()||'{}')}catch(e){return {}}}\nfunction janusCycleTotal(r){let cs=(r&&r.cores)||{},n=0;Object.keys(cs).forEach(k=>n+=Number(cs[k].cycle_count||0));return n}\nfunction janusUnifiedHome(){let r=janusLocalSnapshot(),cs=r.cores||{},total=janusCycleTotal(r),sync=String(r.sync_state||'unknown'),connected=sync==='connected';let coreCount=Object.keys(cs).length;homeCard.innerHTML=`<b>${connected?'Connected · local and online JANUS':'Local JANUS active'}</b><p>This device: <b>${coreCount||11} cores · ${total} cycles</b><br>Phase: ${esc(r.phase||'unknown')}<br>Global link: <b>${connected?'authenticated heartbeat confirmed':esc(sync.replaceAll('-',' '))}</b><br>Last sync: ${r.last_sync_at?fmt(new Date(Number(r.last_sync_at)).toISOString()):'not yet confirmed'}<br>Storage: ${esc(r.storage_backend||(r.persistent_storage?'persistent':'local app storage'))}</p><div class="small">All runtime screens use this device snapshot as the authoritative local state. Global telemetry is shown separately and never replaces live local core state.</div>`}\nasync function janusAuthenticatedHeartbeat(){if(!profile||!token)return;try{let r=janusLocalSnapshot(),cs=r.cores||{},cycles={};Object.keys(cs).forEach(k=>cycles[k]=Number(cs[k].cycle_count||0));let payload={device_id:r.installation_id||('android-'+String(accountId||profile||'device')),platform:'android',client_version:'0.58',phase:r.phase||'unknown',consensus:String(r.consensus||'').slice(0,1000),interface:String(r.interface||'').slice(0,1000),cycles:cycles,observe_events:[],memories:[],conclusions:[]};let x=await api('POST','/core-sync/exchange',payload);Android.globalHeartbeatResult(true,'online '+String((x.presence&&x.presence.online)||0));if(document.getElementById('options').classList.contains('active'))janusUnifiedHome();}catch(e){try{Android.globalHeartbeatResult(false,String(e&&e.message||e||'heartbeat failed'));if(document.getElementById('options').classList.contains('active'))janusUnifiedHome();}catch(_){}}}\nsetInterval(janusAuthenticatedHeartbeat,15000);setTimeout(janusAuthenticatedHeartbeat,1200);\n'''
anchor = 'loadSettings();if(token&&localStorage.janusProfile)'
if anchor not in h:
    raise SystemExit('index bootstrap anchor not found')
if 'janusAuthenticatedHeartbeat' not in h:
    h = h.replace(anchor, insert + anchor)

old_send = "async function sendChat(){let m=composer.value.trim();if(!m)return;composer.value='';addMsg('You',m);setStatus('Interface responding');try{let r=await api('POST','/desktop/chat',{profile_id:profile,message:m,local_runtime_evidence:localEvidenceForChat(),client_message_id:'android-'+Date.now()+'-'+Math.random().toString(36).slice(2)});addMsg('JANUS',r.reply||r.response||JSON.stringify(r));if(r.generated_image)await addGeneratedImage(r.generated_image);setStatus('Interface active');refresh('messages')}catch(e){addMsg('System',e.message);setStatus('Offline · message retained')}}"
new_send = "async function sendChat(){let m=composer.value.trim();if(!m)return;composer.value='';addMsg('You',m);setStatus('Interface responding');try{let r=await api('POST','/desktop/chat',{profile_id:profile,message:m,local_runtime_evidence:localEvidenceForChat(),client_message_id:'android-'+Date.now()+'-'+Math.random().toString(36).slice(2)});addMsg('JANUS',r.reply||r.response||JSON.stringify(r));if(r.generated_image)await addGeneratedImage(r.generated_image);if(r.mode==='local_offline_queue'||r.stored_locally){addMsg('System','Saved locally. Online JANUS has not acknowledged this message yet.')}else{addMsg('System','✓ Online JANUS received and acknowledged this message.')}setStatus('Interface active');refresh('messages');setTimeout(janusAuthenticatedHeartbeat,120)}catch(e){addMsg('System',e.message);setStatus('Offline · message retained')}}"
if old_send in h:
    h = h.replace(old_send, new_send)

# Make Options and Cores use the same authoritative local snapshot after every refresh.
old_refresh_wrap = "if(window.refresh&&!window.__janusCoreRefreshWrapped){window.__janusCoreRefreshWrapped=true;var oldRefresh=window.refresh;window.refresh=async function(p){var x;try{x=await oldRefresh(p);}catch(e){}if(p==='cores')setTimeout(window.refreshCoreTopology,80);if(p==='observe'||p==='memory'||p==='activity')setTimeout(function(){window.janusLocalEvidence(p);},80);return x;};}"
new_refresh_wrap = "if(window.refresh&&!window.__janusCoreRefreshWrapped){window.__janusCoreRefreshWrapped=true;var oldRefresh=window.refresh;window.refresh=async function(p){var x;try{x=await oldRefresh(p);}catch(e){}if(p==='options')setTimeout(window.janusUnifiedHome,60);if(p==='cores')setTimeout(function(){window.refreshCoreTopology();var cl=document.getElementById('coreList');if(cl)cl.innerHTML='';},80);if(p==='observe'||p==='memory'||p==='activity')setTimeout(function(){window.janusLocalEvidence(p);},80);return x;};}"
if old_refresh_wrap in h:
    h = h.replace(old_refresh_wrap, new_refresh_wrap)

old_show_wrap = "if(window.show&&!window.__janusCoreShowWrapped){window.__janusCoreShowWrapped=true;var oldShow=window.show;window.show=function(p){var x=oldShow(p);if(p==='cores')setTimeout(window.refreshCoreTopology,80);if(p==='observe'||p==='memory'||p==='activity')setTimeout(function(){window.janusLocalEvidence(p);},120);return x;};}"
new_show_wrap = "if(window.show&&!window.__janusCoreShowWrapped){window.__janusCoreShowWrapped=true;var oldShow=window.show;window.show=function(p){var x=oldShow(p);if(p==='options')setTimeout(window.janusUnifiedHome,60);if(p==='cores')setTimeout(function(){window.refreshCoreTopology();var cl=document.getElementById('coreList');if(cl)cl.innerHTML='';},80);if(p==='observe'||p==='memory'||p==='activity')setTimeout(function(){window.janusLocalEvidence(p);},120);return x;};}"
if old_show_wrap in h:
    h = h.replace(old_show_wrap, new_show_wrap)

html.write_text(h, encoding='utf-8')
print('Patched Android v0.58 authenticated heartbeat + unified local telemetry + explicit online delivery acknowledgement')
