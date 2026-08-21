from pathlib import Path

p=Path('android/app/src/main/java/com/vardath/janus/JanusLocalCoreRuntime.java')
s=p.read_text(encoding='utf-8')

old='''if(code<400){JSONObject server=new JSONObject(b.toString()).optJSONObject("server");if(server!=null){String rc=server.optString("consensus","");String ri=server.optString("interface","");String fb=clip("global feedback; consensus="+rc+"; interface="+ri,520);if(!(rc.isEmpty()&&ri.isEmpty())){cores.get("context").inbox.addLast("[feedback-only] "+fb);cores.get("counterpoint").inbox.addLast("[feedback-only] check disagreement/novelty: "+fb);record("interface","context","interaction","Compressed global feedback was routed through specialist review rather than directly back into Consensus/Interface.");serviceBurst(true);}}if(pendingBatchMaxAt>lastSyncAt)lastSyncAt=pendingBatchMaxAt;lastSyncState="connected";persist();}else lastSyncState="server-error-"+code;'''
new='''if(code<400){JSONObject envelope=new JSONObject(b.toString());JSONObject remoteDeliberation=envelope.optJSONObject("active_deliberation");if(remoteDeliberation!=null){String remoteTopic=remoteDeliberation.optString("topic","").trim();if(!remoteTopic.isEmpty()&&!remoteTopic.equals(activeDeliberation)){activeDeliberation=clip(remoteTopic,1200);deliberationPassCount=0;lastDeliberationAt=0L;record("interface",null,"deliberation_started","Synced active server deliberation: "+activeDeliberation);}}JSONObject server=envelope.optJSONObject("server");if(server!=null){String rc=server.optString("consensus","");String ri=server.optString("interface","");String fb=clip("global feedback; consensus="+rc+"; interface="+ri,520);if(!(rc.isEmpty()&&ri.isEmpty())){if(activeDeliberation==null||activeDeliberation.isEmpty()){cores.get("context").inbox.addLast("[feedback-only] "+fb);cores.get("counterpoint").inbox.addLast("[feedback-only] check disagreement/novelty: "+fb);record("interface","context","interaction","Compressed global feedback was routed through specialist review rather than directly back into Consensus/Interface.");serviceBurst(true);}else{record("interface",null,"maintenance","Global feedback arrived but active user-directed deliberation retained priority.");}}if(pendingBatchMaxAt>lastSyncAt)lastSyncAt=pendingBatchMaxAt;lastSyncState="connected";persist();}else lastSyncState="server-error-"+code;'''

if 'Synced active server deliberation:' not in s:
    if old not in s:
        raise SystemExit('forward-routing sync block not found for deliberation sync patch')
    s=s.replace(old,new,1)

required=['active_deliberation','Synced active server deliberation:','active user-directed deliberation retained priority']
missing=[x for x in required if x not in s]
if missing:
    raise SystemExit('Android deliberation sync verification missing: '+repr(missing))

p.write_text(s,encoding='utf-8')
print('Android server-to-local deliberation sync patch applied')
