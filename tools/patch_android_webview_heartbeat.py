from pathlib import Path

runtime = Path('android/app/src/main/java/com/vardath/janus/JanusLocalCoreRuntime.java')
s = runtime.read_text(encoding='utf-8')
for old in ('0.56','0.57','0.58'):
    s = s.replace(f'"client_version","{old}"', '"client_version","0.59"')

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
if 'WebSettings.LOAD_NO_CACHE' not in a:
    a = a.replace('s.setDomStorageEnabled(true);', 's.setDomStorageEnabled(true);\n        s.setCacheMode(WebSettings.LOAD_NO_CACHE);\n        web.clearCache(true);')
activity.write_text(a, encoding='utf-8')

html = Path('android/app/src/main/assets/index.html')
h = html.read_text(encoding='utf-8')
insert = '''\nfunction janusLocalSnapshot(){try{return JSON.parse(Android.localCoreStatus()||'{}')}catch(e){return {}}}\nfunction janusCycleTotal(r){let cs=(r&&r.cores)||{},n=0;Object.keys(cs).forEach(k=>n+=Number(cs[k].cycle_count||0));return n}\nfunction janusLatestEvent(r){let e=(r&&r.observe_events)||[];return e.length?e[e.length-1]:null}\nfunction janusLiveCardHtml(){let r=janusLocalSnapshot(),cs=r.cores||{},total=janusCycleTotal(r),ev=janusLatestEvent(r),sync=String(r.sync_state||'unknown'),connected=sync==='connected',coreCount=Object.keys(cs).length||11;return `<div class="card"><b>LIVE LOCAL JANUS · v0.59</b><p><b>${coreCount} cores · ${total} completed cycles</b><br>Phase: ${esc(r.phase||'unknown')}<br>Global link: ${connected?'authenticated / connected':esc(sync.replaceAll('-',' '))}<br>Last sync: ${r.last_sync_at?fmt(new Date(Number(r.last_sync_at)).toISOString()):'not yet confirmed'}</p><div class="small">${ev?('Latest local activity: '+esc((ev.core_name||'core').replaceAll('_',' '))+' · '+esc(ev.detail||ev.event_type||'activity')):'Waiting for first local activity event…'}</div></div>`}\nfunction janusUnifiedHome(){homeCard.innerHTML=janusLiveCardHtml()+`<div class="card"><div class="small">This device snapshot is the authoritative local runtime state. Global telemetry is secondary and never replaces these counters.</div></div>`}\nfunction janusRefreshVisibleLocal(){if(!profile)return;let opt=document.getElementById('options'),obs=document.getElementById('observe'),cores=document.getElementById('cores');if(opt&&opt.classList.contains('active'))janusUnifiedHome();if(obs&&obs.classList.contains('active')){let marker=document.getElementById('observeLiveState');if(!marker){marker=document.createElement('div');marker.id='observeLiveState';observeList.parentNode.insertBefore(marker,observeList);}marker.innerHTML=janusLiveCardHtml();}if(cores&&cores.classList.contains('active')){let host=document.getElementById('coreTopology');if(host){let r=janusLocalSnapshot();host.innerHTML=janusLiveCardHtml()+window.renderCoreSide('This device · local JANUS',r,true);let cl=document.getElementById('coreList');if(cl)cl.innerHTML='';}}}\nasync function janusAuthenticatedHeartbeat(){if(!profile||!token)return;try{let r=janusLocalSnapshot(),cs=r.cores||{},cycles={};Object.keys(cs).forEach(k=>cycles[k]=Number(cs[k].cycle_count||0));let payload={device_id:r.installation_id||('android-'+String(accountId||profile||'device')),platform:'android',client_version:'0.59',phase:r.phase||'unknown',consensus:String(r.consensus||'').slice(0,1000),interface:String(r.interface||'').slice(0,1000),cycles:cycles,observe_events:[],memories:[],conclusions:[]};let x=await api('POST','/core-sync/exchange',payload);Android.globalHeartbeatResult(true,'online '+String((x.presence&&x.presence.online)||0));janusRefreshVisibleLocal();}catch(e){try{Android.globalHeartbeatResult(false,String(e&&e.message||e||'heartbeat failed'));janusRefreshVisibleLocal();}catch(_){}}}\nif(window.refresh&&!window.__janusUnifiedRefresh){window.__janusUnifiedRefresh=true;let previousRefresh=window.refresh;window.refresh=async function(p){let x;try{x=await previousRefresh(p)}catch(e){}setTimeout(janusRefreshVisibleLocal,40);return x}}\nif(window.show&&!window.__janusUnifiedShow){window.__janusUnifiedShow=true;let previousShow=window.show;window.show=function(p){let x=previousShow(p);setTimeout(janusRefreshVisibleLocal,60);return x}}\nsetInterval(janusAuthenticatedHeartbeat,15000);setInterval(janusRefreshVisibleLocal,2000);setTimeout(janusAuthenticatedHeartbeat,1200);setTimeout(janusRefreshVisibleLocal,500);\n'''
anchor = 'loadSettings();if(token&&localStorage.janusProfile)'
if anchor not in h:
    raise SystemExit('index bootstrap anchor not found')
if 'janusRefreshVisibleLocal' not in h:
    h = h.replace(anchor, insert + anchor)

old_send = "async function sendChat(){let m=composer.value.trim();if(!m)return;composer.value='';addMsg('You',m);setStatus('Interface responding');try{let r=await api('POST','/desktop/chat',{profile_id:profile,message:m,local_runtime_evidence:localEvidenceForChat(),client_message_id:'android-'+Date.now()+'-'+Math.random().toString(36).slice(2)});addMsg('JANUS',r.reply||r.response||JSON.stringify(r));if(r.generated_image)await addGeneratedImage(r.generated_image);setStatus('Interface active');refresh('messages')}catch(e){addMsg('System',e.message);setStatus('Offline · message retained')}}"
new_send = "async function sendChat(){let m=composer.value.trim();if(!m)return;composer.value='';addMsg('You',m);setStatus('Interface responding');try{let r=await api('POST','/desktop/chat',{profile_id:profile,message:m,local_runtime_evidence:localEvidenceForChat(),client_message_id:'android-'+Date.now()+'-'+Math.random().toString(36).slice(2)});addMsg('JANUS',r.reply||r.response||JSON.stringify(r));if(r.generated_image)await addGeneratedImage(r.generated_image);if(r.mode==='local_offline_queue'||r.stored_locally){addMsg('System','Saved locally. Online JANUS has not acknowledged this message yet.')}else{addMsg('System','✓ Online JANUS received and acknowledged this message.')}setStatus('Interface active');refresh('messages');setTimeout(janusAuthenticatedHeartbeat,120)}catch(e){addMsg('System',e.message);setStatus('Offline · message retained')}}"
if old_send in h:
    h = h.replace(old_send, new_send)

html.write_text(h, encoding='utf-8')
print('Patched Android v0.59: visible live local telemetry, 2-second refresh, cache bypass, heartbeat and explicit delivery acknowledgement')
