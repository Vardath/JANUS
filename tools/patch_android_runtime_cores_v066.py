from pathlib import Path

runtime = Path('android/app/src/main/java/com/vardath/janus/JanusLocalCoreRuntime.java')
r = runtime.read_text(encoding='utf-8')

# Keep server snapshot storage/getter available even if older patches change shape.
if 'private volatile String lastServerStatus=' not in r:
    r = r.replace('private final String installationId;', 'private final String installationId;\n    private volatile String lastServerStatus="";')
if 'core_server_status' not in r:
    r = r.replace('lastSyncAt=prefs.getLong("core_last_sync_at",0L);', 'lastSyncAt=prefs.getLong("core_last_sync_at",0L); lastServerStatus=prefs.getString("core_server_status","");')
if 'serverStatusJson()' not in r:
    r = r.replace('private JSONObject summary() throws Exception', 'synchronized String serverStatusJson(){return lastServerStatus==null?"":lastServerStatus;}\n\n    private JSONObject summary() throws Exception')

# Capture successful /core-sync/exchange server payload at the actual parse point.
needle='JSONObject server=new JSONObject(b.toString()).optJSONObject("server");'
if needle in r and 'lastServerStatus=server.toString()' not in r:
    r=r.replace(needle, needle+'if(server!=null){lastServerStatus=server.toString();prefs.edit().putString("core_server_status",lastServerStatus).apply();}',1)

r=r.replace('"client_version","0.65"','"client_version","0.66"')
runtime.write_text(r,encoding='utf-8')

activity=Path('android/app/src/main/java/com/vardath/janus/MainActivity.java')
a=activity.read_text(encoding='utf-8')
if '@JavascriptInterface public String serverCoreStatus()' not in a:
    marker='@JavascriptInterface public void googleSignIn()'
    if marker in a:
        a=a.replace(marker,'@JavascriptInterface public String serverCoreStatus() { try { return JanusLocalCoreRuntime.get(MainActivity.this).serverStatusJson(); } catch (Exception e) { return ""; } }\n        '+marker,1)
for v in ('0.60','0.61','0.62','0.63','0.64','0.65'):
    a=a.replace(f'LIVE LOCAL JANUS · v{v}','LIVE LOCAL JANUS · v0.66')
activity.write_text(a,encoding='utf-8')

html=Path('android/app/src/main/assets/index.html')
h=html.read_text(encoding='utf-8')
for v in ('0.59','0.60','0.61','0.62','0.63','0.64','0.65'):
    h=h.replace(f'LIVE LOCAL JANUS · v{v}','LIVE LOCAL JANUS · v0.66')
    h=h.replace(f"client_version:'{v}'", "client_version:'0.66'")

# The previous screen rendered once and then sat on WAITING FOR HEARTBEAT even
# after native sync had stored the snapshot. Refresh the Cores surface while it
# is visible so the next heartbeat appears automatically.
if '__janusCoreHeartbeatPollV066' not in h:
    inject="""
<script>
(function(){
  if(window.__janusCoreHeartbeatPollV066)return;
  window.__janusCoreHeartbeatPollV066=true;
  setInterval(function(){
    try{
      var cores=document.getElementById('cores');
      if(cores && cores.classList.contains('active') && typeof window.refreshCoreTopology==='function'){
        window.refreshCoreTopology();
      }
    }catch(e){}
  },3000);
})();
</script>
"""
    h=h.replace('</body>',inject+'</body>')
html.write_text(h,encoding='utf-8')
print('Patched Android v0.66: heartbeat snapshot capture + live Cores polling')