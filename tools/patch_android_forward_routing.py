from pathlib import Path

p = Path('android/app/src/main/java/com/vardath/janus/JanusLocalCoreRuntime.java')
s = p.read_text(encoding='utf-8')

old_route = '''    private void route(String from,String text){
        if(Arrays.asList("evidence","logic","counterpoint").contains(from))send(from,"left_hemisphere",text);
        else if(Arrays.asList("context","memory","novelty").contains(from))send(from,"right_hemisphere",text);
        else if("safety".equals(from)){send(from,"left_hemisphere",text);send(from,"right_hemisphere",text);send(from,"consensus",text);send(from,"interface",text);}
        else if("left_hemisphere".equals(from)){send(from,"right_hemisphere",text);send(from,"consensus",text);}
        else if("right_hemisphere".equals(from)){send(from,"left_hemisphere",text);send(from,"consensus",text);}
        else if("consensus".equals(from)){lastConsensus=text;send(from,"interface",text);send(from,"left_hemisphere",text);send(from,"right_hemisphere",text);}
        else if("interface".equals(from)){lastInterface=text;send(from,"consensus",text);}
    }
'''
new_route = '''    private void route(String from,String text){
        // Ordinary cognition is strictly forward-only:
        // specialists -> assigned hemisphere -> consensus -> interface.
        // Consensus/Interface are not recycled as the next primary topic.
        if(Arrays.asList("evidence","logic","counterpoint").contains(from))send(from,"left_hemisphere",text);
        else if(Arrays.asList("context","memory","novelty").contains(from))send(from,"right_hemisphere",text);
        else if("safety".equals(from)){send(from,"left_hemisphere",text);send(from,"right_hemisphere",text);send(from,"consensus",text);}
        else if("left_hemisphere".equals(from))send(from,"consensus",text);
        else if("right_hemisphere".equals(from))send(from,"consensus",text);
        else if("consensus".equals(from)){lastConsensus=text;send(from,"interface",text);}
        else if("interface".equals(from))lastInterface=text;
    }
'''

old_sync = '''if(code<400){JSONObject server=new JSONObject(b.toString()).optJSONObject("server");if(server!=null){String rc=server.optString("consensus","");String ri=server.optString("interface","");if(!rc.isEmpty())send("interface","consensus","global consensus: "+rc);if(!ri.isEmpty())send("consensus","interface","global interface: "+ri);serviceBurst(true);}if(pendingBatchMaxAt>lastSyncAt)lastSyncAt=pendingBatchMaxAt;lastSyncState="connected";persist();}else lastSyncState="server-error-"+code;'''
new_sync = '''if(code<400){JSONObject server=new JSONObject(b.toString()).optJSONObject("server");if(server!=null){String rc=server.optString("consensus","");String ri=server.optString("interface","");String fb=clip("global feedback; consensus="+rc+"; interface="+ri,520);if(!fb.trim().isEmpty()){cores.get("context").inbox.addLast("[feedback-only] "+fb);cores.get("counterpoint").inbox.addLast("[feedback-only] check disagreement/novelty: "+fb);record("interface","context","interaction","Compressed global feedback was routed through specialist review rather than directly back into Consensus/Interface.");serviceBurst(true);}}if(pendingBatchMaxAt>lastSyncAt)lastSyncAt=pendingBatchMaxAt;lastSyncState="connected";persist();}else lastSyncState="server-error-"+code;'''

if old_route not in s:
    raise SystemExit('Expected Android route block not found; refusing unsafe patch')
if old_sync not in s:
    raise SystemExit('Expected Android sync reinjection block not found; refusing unsafe patch')

s = s.replace(old_route, new_route, 1).replace(old_sync, new_sync, 1)
p.write_text(s, encoding='utf-8')
