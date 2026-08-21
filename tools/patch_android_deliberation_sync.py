from pathlib import Path
import re

p = Path('android/app/src/main/java/com/vardath/janus/JanusLocalCoreRuntime.java')
s = p.read_text(encoding='utf-8')

new = '''if(code<400){JSONObject envelope=new JSONObject(b.toString());JSONObject remoteDeliberation=envelope.optJSONObject("active_deliberation");if(remoteDeliberation!=null){String remoteTopic=remoteDeliberation.optString("topic","").trim();if(!remoteTopic.isEmpty()&&!remoteTopic.equals(activeDeliberation)){activeDeliberation=clip(remoteTopic,1200);deliberationPassCount=0;lastDeliberationAt=0L;record("interface",null,"deliberation_started","Synced active server deliberation: "+activeDeliberation);}}JSONObject server=envelope.optJSONObject("server");if(server!=null){String rc=server.optString("consensus","");String ri=server.optString("interface","");String fb=clip("global feedback; consensus="+rc+"; interface="+ri,520);if(!(rc.isEmpty()&&ri.isEmpty())){if(activeDeliberation==null||activeDeliberation.isEmpty()){cores.get("context").inbox.addLast("[feedback-only] "+fb);cores.get("counterpoint").inbox.addLast("[feedback-only] check disagreement/novelty: "+fb);record("interface","context","interaction","Compressed global feedback was routed through specialist review rather than directly back into Consensus/Interface.");serviceBurst(true);}else{record("interface",null,"maintenance","Global feedback arrived but active user-directed deliberation retained priority.");}}if(pendingBatchMaxAt>lastSyncAt)lastSyncAt=pendingBatchMaxAt;lastSyncState="connected";persist();}else lastSyncState="server-error-"+code;'''

if 'Synced active server deliberation:' not in s:
    pat = re.compile(
        r'if\(code<400\)\{JSONObject\s+server=new JSONObject\(b\.toString\(\)\)\.optJSONObject\("server"\);.*?'
        r'lastSyncState="connected";persist\(\);\}else lastSyncState="server-error-"\+code;',
        re.S,
    )
    m = pat.search(s)
    if not m:
        raise SystemExit('forward-routing sync block not found structurally for deliberation sync patch')
    s = s[:m.start()] + new + s[m.end():]

required = [
    'JSONObject remoteDeliberation=envelope.optJSONObject("active_deliberation")',
    'Synced active server deliberation:',
    'active user-directed deliberation retained priority',
    'if(activeDeliberation==null||activeDeliberation.isEmpty())',
]
missing = [x for x in required if x not in s]
if missing:
    raise SystemExit('Android deliberation sync verification missing: ' + repr(missing))

# Ensure the old direct envelope parse cannot remain alongside the new block.
if 'JSONObject server=new JSONObject(b.toString()).optJSONObject("server")' in s:
    raise SystemExit('Legacy Android sync parse still present after deliberation sync patch')

p.write_text(s, encoding='utf-8')
print('Android server-to-local deliberation sync patch applied and verified')
