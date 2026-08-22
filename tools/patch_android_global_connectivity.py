from pathlib import Path

p = Path('android/app/src/main/java/com/vardath/janus/JanusLocalCoreRuntime.java')
s = p.read_text(encoding='utf-8')
s = s.replace(
    'return new JSONObject().put("device_id",installationId).put("phase",phase).put("consensus",lastConsensus).put("interface",lastInterface).put("cycles",cycles).put("observe_events",unsyncedObserveArray());',
    'JSONArray mem=new JSONArray();java.util.List<String> ml=new java.util.ArrayList<>(localMemories);for(int i=Math.max(0,ml.size()-8);i<ml.size();i++)mem.put(ml.get(i));return new JSONObject().put("device_id",installationId).put("platform","android").put("client_version","0.54").put("phase",phase).put("consensus",lastConsensus).put("interface",lastInterface).put("cycles",cycles).put("observe_events",unsyncedObserveArray()).put("memories",mem);'
)
old = 'if(code<400){JSONObject server=new JSONObject(b.toString()).optJSONObject("server");if(server!=null){String rc=server.optString("consensus","");String ri=server.optString("interface","");if(!rc.isEmpty())send("interface","consensus","global consensus: "+rc);if(!ri.isEmpty())send("consensus","interface","global interface: "+ri);serviceBurst(true);}if(pendingBatchMaxAt>lastSyncAt)lastSyncAt=pendingBatchMaxAt;lastSyncState="connected";persist();}else lastSyncState="server-error-"+code;'
new = 'if(code<400){JSONObject response=new JSONObject(b.toString());JSONObject shared=response.optJSONObject("shared_state");if(shared!=null){JSONArray items=shared.optJSONArray("items");if(items!=null)for(int i=0;i<items.length();i++){JSONObject item=items.optJSONObject(i);if(item==null)continue;String kind=item.optString("kind","remote");String text=item.optString("text","");if(text.isEmpty())continue;String tagged="global-grounding ["+kind+"]: "+text;send("interface","evidence",tagged);send("interface","context",tagged);send("interface","memory",tagged);send("interface","counterpoint",tagged);}serviceBurst(true);}if(pendingBatchMaxAt>lastSyncAt)lastSyncAt=pendingBatchMaxAt;lastSyncState=response.optBoolean("sync_degraded",false)?"degraded":"connected";persist();}else lastSyncState="server-error-"+code;'
if old not in s:
    raise SystemExit('expected Android sync block not found')
s = s.replace(old, new)
p.write_text(s, encoding='utf-8')

html = Path('android/app/src/main/assets/index.html')
h = html.read_text(encoding='utf-8')
h = h.replace("api('GET','/desktop/runtime-cores?username='+encodeURIComponent(profile))", "api('GET','/core-sync/status')")
h = h.replace("let rt=r.runtime||{},cs=rt.cores||{};", "let rt=r.runtime||r||{},cs=rt.cores||{};")
html.write_text(h, encoding='utf-8')
print('Patched Android authenticated presence + tagged selective global grounding + live global status')
