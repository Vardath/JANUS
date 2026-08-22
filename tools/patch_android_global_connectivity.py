from pathlib import Path

p = Path('android/app/src/main/java/com/vardath/janus/JanusLocalCoreRuntime.java')
s = p.read_text(encoding='utf-8')
s = s.replace(
    'return new JSONObject().put("device_id",installationId).put("phase",phase).put("consensus",lastConsensus).put("interface",lastInterface).put("cycles",cycles).put("observe_events",unsyncedObserveArray());',
    'JSONArray mem=new JSONArray();java.util.List<String> ml=new java.util.ArrayList<>(localMemories);for(int i=Math.max(0,ml.size()-8);i<ml.size();i++)mem.put(ml.get(i));return new JSONObject().put("device_id",installationId).put("platform","android").put("client_version","0.55").put("phase",phase).put("consensus",lastConsensus).put("interface",lastInterface).put("cycles",cycles).put("observe_events",unsyncedObserveArray()).put("memories",mem);'
)
old = 'if(code<400){JSONObject envelope=new JSONObject(b.toString());JSONObject remoteDeliberation=envelope.optJSONObject("active_deliberation");if(remoteDeliberation!=null){String remoteTopic=remoteDeliberation.optString("topic","").trim();if(!remoteTopic.isEmpty()&&!remoteTopic.equals(activeDeliberation)){activeDeliberation=clip(remoteTopic,1200);deliberationPassCount=0;lastDeliberationAt=0L;record("interface",null,"deliberation_started","Synced active server deliberation: "+activeDeliberation);}}JSONObject server=envelope.optJSONObject("server");if(server!=null){String rc=server.optString("consensus","");String ri=server.optString("interface","");String fb=clip("global feedback; consensus="+rc+"; interface="+ri,520);if(!(rc.isEmpty()&&ri.isEmpty())){if(activeDeliberation==null||activeDeliberation.isEmpty()){cores.get("context").inbox.addLast("[feedback-only] "+fb);cores.get("counterpoint").inbox.addLast("[feedback-only] check disagreement/novelty: "+fb);record("interface","context","interaction","Compressed global feedback was routed through specialist review rather than directly back into Consensus/Interface.");serviceBurst(true);}else{record("interface",null,"maintenance","Global feedback arrived but active user-directed deliberation retained priority.");}}}if(pendingBatchMaxAt>lastSyncAt)lastSyncAt=pendingBatchMaxAt;lastSyncState="connected";persist();}else lastSyncState="server-error-"+code;'
new = 'if(code<400){JSONObject envelope=new JSONObject(b.toString());JSONObject remoteDeliberation=envelope.optJSONObject("active_deliberation");if(remoteDeliberation!=null){String remoteTopic=remoteDeliberation.optString("topic","").trim();if(!remoteTopic.isEmpty()&&!remoteTopic.equals(activeDeliberation)){activeDeliberation=clip(remoteTopic,1200);deliberationPassCount=0;lastDeliberationAt=0L;record("interface",null,"deliberation_started","Synced active server deliberation: "+activeDeliberation);}}JSONObject shared=envelope.optJSONObject("shared_state");if(shared!=null){JSONArray items=shared.optJSONArray("items");if(items!=null)for(int i=0;i<items.length();i++){JSONObject item=items.optJSONObject(i);if(item==null)continue;String kind=item.optString("kind","remote");String text=item.optString("text","").trim();if(text.isEmpty())continue;String tagged="global-grounding ["+kind+"]: "+text;cores.get("evidence").inbox.addLast(tagged);cores.get("context").inbox.addLast(tagged);cores.get("memory").inbox.addLast(tagged);cores.get("counterpoint").inbox.addLast(tagged);record("interface","context","interaction","Tagged global material entered through specialist review: "+kind);}}if(pendingBatchMaxAt>lastSyncAt)lastSyncAt=pendingBatchMaxAt;lastSyncState=envelope.optBoolean("sync_degraded",false)?"degraded":"connected";serviceBurst(true);persist();}else lastSyncState="server-error-"+code;'
if old not in s:
    raise SystemExit('expected post-deliberation Android sync block not found')
s = s.replace(old, new)
if 'void syncNow()' not in s:
    marker = 'synchronized void start(){if(started)return;started=true;executor.scheduleAtFixedRate(this::tickSafe,0,5,TimeUnit.SECONDS);executor.scheduleAtFixedRate(this::syncSafe,10,15,TimeUnit.SECONDS);}'
    if marker not in s:
        raise SystemExit('Android local runtime start marker not found')
    s = s.replace(marker, marker + '\n    void syncNow(){executor.execute(this::syncSafe);}')
if 'send("interface","consensus","global consensus:' in s or 'send("consensus","interface","global interface:' in s:
    raise SystemExit('direct global-to-consensus/interface injection still present')
p.write_text(s, encoding='utf-8')

html = Path('android/app/src/main/assets/index.html')
h = html.read_text(encoding='utf-8')
h = h.replace("api('GET','/desktop/runtime-cores?username='+encodeURIComponent(profile))", "api('GET','/core-sync/status')")
h = h.replace("let rt=r.runtime||{},cs=rt.cores||{};", "let rt=r.runtime||r||{},cs=rt.cores||{};")
html.write_text(h, encoding='utf-8')

activity = Path('android/app/src/main/java/com/vardath/janus/MainActivity.java')
a = activity.read_text(encoding='utf-8')
old_fetch = "var global=await api('GET','/desktop/runtime-cores?username='+encodeURIComponent(profile));var gr=global.runtime||global;host.innerHTML='<div class=\\\"card\\\"><b>JANUS 11-core topology</b><p>7 specialist perspectives feed two hemispheres. The hemispheres feed the consensus reader/giver. Consensus feeds the interface core that represents JANUS to you.</p><div class=\\\"small\\\">The local society runs independently on this device. Server synchronization is optional and does not power local core cycles.</div></div>'+window.renderCoreSide('This device · local JANUS',local,true)+window.renderCoreSide('Online · global JANUS',gr,false);"
new_fetch = "var gr=await api('GET','/core-sync/status');var connected=Number(gr.remote_clients||0)>0;var title=connected?'Connected · global JANUS':'Reachable · awaiting authenticated heartbeat';host.innerHTML='<div class=\\\"card\\\"><b>JANUS 11-core topology</b><p>7 specialist perspectives feed two hemispheres. The hemispheres feed the consensus reader/giver. Consensus feeds the interface core that represents JANUS to you.</p><div class=\\\"small\\\">The local society runs independently on this device. Global status is only called connected after an authenticated heartbeat is registered.</div></div>'+window.renderCoreSide('This device · local JANUS',local,true)+window.renderCoreSide(title,gr,false);"
if old_fetch not in a:
    raise SystemExit('MainActivity legacy global topology request not found')
a = a.replace(old_fetch, new_fetch)
a = a.replace("esc(r.storage_backend||(r.persistent_storage?'persistent':'unknown'))", "esc(r.storage_backend||(r.persistent_storage===true?'persistent':(r.persistent_storage===false?'not persistent':'unknown')))")
old_token = 'getSharedPreferences("janus", MODE_PRIVATE).edit().putString("access_token", token).apply();\n                return token;'
new_token = 'getSharedPreferences("janus", MODE_PRIVATE).edit().putString("access_token", token).apply();\n                JanusLocalCoreRuntime.get(MainActivity.this).syncNow();\n                return token;'
if old_token not in a:
    raise SystemExit('MainActivity access token persistence block not found')
a = a.replace(old_token, new_token)
activity.write_text(a, encoding='utf-8')
print('Patched Android v0.55 authenticated heartbeat, presence status, and honest connected/reachable UI')
