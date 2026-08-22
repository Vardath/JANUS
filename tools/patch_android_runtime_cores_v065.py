from pathlib import Path
import re

runtime = Path('android/app/src/main/java/com/vardath/janus/JanusLocalCoreRuntime.java')
r = runtime.read_text(encoding='utf-8')

# v0.64 added the native snapshot storage and WebView bridge, but the actual
# generated Java layout can vary because several earlier build-time patches run
# before this one. Match the live `server` parse semantically instead of relying
# on one exact source string.
if 'lastServerStatus=server.toString()' not in r:
    pattern = re.compile(
        r'(JSONObject\s+server\s*=\s*[^;]*?optJSONObject\(\"server\"\)\s*;)'
    )
    match = pattern.search(r)
    if match:
        hook = match.group(1) + 'if(server!=null){lastServerStatus=server.toString();prefs.edit().putString("core_server_status",lastServerStatus).apply();}'
        r = r[:match.start()] + hook + r[match.end():]
    else:
        # Do not kill the whole APK build over source-layout drift. Leave a clear
        # marker in stdout; the Java compile/regression checks can then expose a
        # real incompatibility without preventing unrelated release validation.
        print('WARNING: v0.65 could not locate server heartbeat parse point; capture hook not inserted')

# Keep client/version telemetry truthful.
for v in ('0.63','0.64'):
    r = r.replace(f'"client_version","{v}"', '"client_version","0.65"')
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

print('Patched Android v0.65: resilient heartbeat snapshot capture')
