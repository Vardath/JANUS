from pathlib import Path

runtime = Path('android/app/src/main/java/com/vardath/janus/JanusLocalCoreRuntime.java')
r = runtime.read_text(encoding='utf-8')

# v0.64 correctly added native snapshot storage and the WebView bridge, but the
# capture hook searched for an obsolete `envelope.optJSONObject("server")`
# pattern. The actual generated runtime parses the exchange response directly.
# Capture that exact server object immediately after it is parsed.
patterns = [
    'JSONObject server=new JSONObject(b.toString()).optJSONObject("server");',
    'JSONObject server = new JSONObject(b.toString()).optJSONObject("server");',
]
inserted = False
for needle in patterns:
    if needle in r:
        replacement = needle + 'if(server!=null){lastServerStatus=server.toString();prefs.edit().putString("core_server_status",lastServerStatus).apply();}'
        if replacement not in r:
            r = r.replace(needle, replacement, 1)
        inserted = True
        break
if not inserted and 'lastServerStatus=server.toString()' not in r:
    raise SystemExit('Could not find live /core-sync/exchange server parse point')

# Keep client/version telemetry truthful.
r = r.replace('"client_version","0.64"', '"client_version","0.65"')
r = r.replace('"client_version","0.63"', '"client_version","0.65"')
runtime.write_text(r, encoding='utf-8')

activity = Path('android/app/src/main/java/com/vardath/janus/MainActivity.java')
a = activity.read_text(encoding='utf-8')
for v in ('0.60','0.61','0.62','0.63','0.64'):
    a = a.replace(f'LIVE LOCAL JANUS · v{v}', 'LIVE LOCAL JANUS · v0.65')
activity.write_text(a, encoding='utf-8')

html = Path('android/app/src/main/assets/index.html')
h = html.read_text(encoding='utf-8')
for v in ('0.59','0.60','0.61','0.62','0.63','0.64'):
    h = h.replace(f'LIVE LOCAL JANUS · v{v}', 'LIVE LOCAL JANUS · v0.65')
    h = h.replace(f"client_version:'{v}'", "client_version:'0.65'")
html.write_text(h, encoding='utf-8')

print('Patched Android v0.65: capture authoritative server snapshot from successful native heartbeat')
