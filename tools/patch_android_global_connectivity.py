from pathlib import Path

p = Path('android/app/src/main/java/com/vardath/janus/JanusLocalCoreRuntime.java')
s = p.read_text(encoding='utf-8')
s = s.replace(
    'return new JSONObject().put("device_id",installationId).put("phase",phase).put("consensus",lastConsensus).put("interface",lastInterface).put("cycles",cycles).put("observe_events",unsyncedObserveArray());',
    'JSONArray mem=new JSONArray();java.util.List<String> ml=new java.util.ArrayList<>(localMemories);for(int i=Math.max(0,ml.size()-8);i<ml.size();i++)mem.put(ml.get(i));return new JSONObject().put("device_id",installationId).put("platform","android").put("client_version","0.54").put("phase",phase).put("consensus",lastConsensus).put("interface",lastInterface).put("cycles",cycles).put("observe_events",unsyncedObserveArray()).put("memories",mem);'
)
old = 'if(code<400){JSONObject envelope=new JSONObject(b.toString());JSONObject remoteDeliberation=envelope.optJSONObject("active_deliberation");if(remoteDeliberation!=null){String remoteTopic=remoteDeliberation.optString("topic","").trim();if(!remoteTopic.isEmpty()&&!remoteTopic.equals(activeDeliberation)){activeDeliberation=clip(remoteTopic,1200);deliberationPassCount=0;lastDeliberationAt=0L;record("interface",null,"deliberation_started","Synced active server deliberation: "+activeDeliberation);}}JSONObject server=envelope.optJSONObject("server");if(server!=null){String rc=server.optString("consensus","");String ri=server.optString("interface","");String fb=clip("global feedback; consensus="+rc+"; interface="+ri,520);if(!(rc.isEmpty()&&ri.isEmpty())){if(activeDeliberation==null||activeDeliberation.isEmpty()){cores.get("context").inbox.addLast("[feedback-only] "+fb);cores.get("counterpoint").inbox.addLast("[feedback-only] check disagreement/novelty: "+fb);record("interface","context","interaction","Compressed global feedback was routed through specialist review rather than directly back into Consensus/Interface.");serviceBurst(true);}else{record("interface",null,"maintenance","Global feedback arrived but active user-directed deliberation retained priority.");}}}if(pendingBatchMaxAt>lastSyncAt)lastSyncAt=pendingBatchMaxAt;lastSyncState="connected";persist();}else lastSyncState="server-error-"+code;'
new = 'if(code<400){JSONObject envelope=new JSONObject(b.toString());JSONObject remoteDeliberation=envelope.optJSONObject("active_deliberation");if(remoteDeliberation!=null){String remoteTopic=remoteDeliberation.optString("topic","").trim();if(!remoteTopic.isEmpty()&&!remoteTopic.equals(activeDeliberation)){activeDeliberation=clip(remoteTopic,1200);deliberationPassCount=0;lastDeliberationAt=0L;record("interface",null,"deliberation_started","Synced active server deliberation: "+activeDeliberation);}}JSONObject shared=envelope.optJSONObject("shared_state");if(shared!=null){JSONArray items=shared.optJSONArray("items");if(items!=null)for(int i=0;i<items.length();i++){JSONObject item=items.optJSONObject(i);if(item==null)continue;String kind=item.optString("kind","remote");String text=item.optString("text","").trim();if(text.isEmpty())continue;String tagged="global-grounding ["+kind+"]: "+text;cores.get("evidence").inbox.addLast(tagged);cores.get("context").inbox.addLast(tagged);cores.get("memory").inbox.addLast(tagged);cores.get("counterpoint").inbox.addLast(tagged);record("interface","context","interaction","Tagged global material entered through specialist review: "+kind);}}if(pendingBatchMaxAt>lastSyncAt)lastSyncAt=pendingBatchMaxAt;lastSyncState=envelope.optBoolean("sync_degraded",false)?"degraded":"connected";serviceBurst(true);persist();}else lastSyncState="server-error-"+code;'
if old not in s:
    raise SystemExit('expected post-deliberation Android sync block not found')
s = s.replace(old, new)
if 'send("interface","consensus","global consensus:' in s or 'send("consensus","interface","global interface:' in s:
    raise SystemExit('direct global-to-consensus/interface injection still present')
p.write_text(s, encoding='utf-8')

html = Path('android/app/src/main/assets/index.html')
h = html.read_text(encoding='utf-8')
h = h.replace("api('GET','/desktop/runtime-cores?username='+encodeURIComponent(profile))", "api('GET','/core-sync/status')")
h = h.replace("let rt=r.runtime||{},cs=rt.cores||{};", "let rt=r.runtime||r||{},cs=rt.cores||{};")
html.write_text(h, encoding='utf-8')
print('Patched Android authenticated presence + tagged selective global grounding + live global status')
