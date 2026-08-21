from pathlib import Path
import re

p = Path('android/app/src/main/java/com/vardath/janus/JanusLocalCoreRuntime.java')
s = p.read_text(encoding='utf-8')

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

if 'Ordinary cognition is strictly forward-only' not in s:
    route_pat = re.compile(r'    private void route\(String from,String text\)\{.*?\n    \}\n', re.S)
    m = route_pat.search(s)
    if not m:
        raise SystemExit('Android route() method not found')
    s = s[:m.start()] + new_route + s[m.end():]

old_sync_re = re.compile(
    r'if\(code<400\)\{JSONObject server=new JSONObject\(b\.toString\(\)\)\.optJSONObject\("server"\);'
    r'if\(server!=null\)\{.*?serviceBurst\(true\);\}'
    r'if\(pendingBatchMaxAt>lastSyncAt\)lastSyncAt=pendingBatchMaxAt;lastSyncState="connected";persist\(\);\}'
    r'else lastSyncState="server-error-"\+code;',
    re.S,
)
new_sync = '''if(code<400){JSONObject server=new JSONObject(b.toString()).optJSONObject("server");if(server!=null){String rc=server.optString("consensus","");String ri=server.optString("interface","");String fb=clip("global feedback; consensus="+rc+"; interface="+ri,520);if(!(rc.isEmpty()&&ri.isEmpty())){cores.get("context").inbox.addLast("[feedback-only] "+fb);cores.get("counterpoint").inbox.addLast("[feedback-only] check disagreement/novelty: "+fb);record("interface","context","interaction","Compressed global feedback was routed through specialist review rather than directly back into Consensus/Interface.");serviceBurst(true);}}if(pendingBatchMaxAt>lastSyncAt)lastSyncAt=pendingBatchMaxAt;lastSyncState="connected";persist();}else lastSyncState="server-error-"+code;'''

if '[feedback-only] check disagreement/novelty:' not in s:
    m = old_sync_re.search(s)
    if not m:
        raise SystemExit('Android sync success block not found')
    s = s[:m.start()] + new_sync + s[m.end():]

# Build-time assertions: fail with a precise message if legacy recursion remains.
legacy_fragments = [
    'send(from,"right_hemisphere",text);send(from,"consensus",text);',
    'send(from,"left_hemisphere",text);send(from,"consensus",text);',
    'send(from,"interface",text);send(from,"left_hemisphere",text);send(from,"right_hemisphere",text);',
    'else if("interface".equals(from)){lastInterface=text;send(from,"consensus",text);}',
    'send("interface","consensus","global consensus:',
    'send("consensus","interface","global interface:',
]
left = [x for x in legacy_fragments if x in s]
if left:
    raise SystemExit('Legacy recursive routing still present: ' + repr(left))

p.write_text(s, encoding='utf-8')
print('Forward-only Android routing verified')
