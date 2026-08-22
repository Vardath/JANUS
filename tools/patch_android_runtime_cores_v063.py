from pathlib import Path

p = Path('android/app/src/main/java/com/vardath/janus/MainActivity.java')
s = p.read_text(encoding='utf-8')

old_full = "var envelope=await api('GET','/desktop/runtime-cores?username='+encodeURIComponent(profile));var gr=envelope.runtime||{};var presence=envelope.presence||{};var online=Number(presence.online||gr.remote_clients||0);var title='SERVER JANUS · LIVE';var list=document.getElementById('coreList');if(list)list.innerHTML='';host.innerHTML='<div class=\\\"card\\\"><b>JANUS 11-core topology</b><p><b>Two independent runtimes are shown below.</b> This device is the local JANUS society. Server JANUS is the persistent online society on Render.</p><div class=\\\"small\\\">Server values come from /desktop/runtime-cores. Local values come directly from this device. Neither substitutes counters for the other.</div></div>'+window.renderCoreSide('THIS DEVICE JANUS · LIVE',local,true)+window.renderCoreSide(title,gr,false)+'<div class=\\\"card\\\"><b>Connection</b><div class=\\\"small\\\">authenticated device clients online '+esc(online)+' · registered '+esc(presence.registered||gr.registered_clients||0)+'</div></div>';"
new_full = "var raw=await api('GET','/core-sync/status');if(typeof raw==='string'){try{raw=JSON.parse(raw);}catch(_){raw={};}}var gr=(raw&&raw.runtime)?raw.runtime:raw;if(!gr||typeof gr!=='object')gr={};var online=Number(gr.remote_clients||0);var registered=Number(gr.registered_clients||0);var list=document.getElementById('coreList');if(list)list.innerHTML='';var hasServer=gr.cores&&Object.keys(gr.cores).length>0;var serverTitle=hasServer?'SERVER JANUS · LIVE':'SERVER JANUS · DATA ERROR';host.innerHTML='<div class=\\\"card\\\"><b>JANUS 11-core topology</b><p><b>Two independent runtimes are shown below.</b> This device is local. Server JANUS is the persistent Render runtime.</p><div class=\\\"small\\\">Server values are read directly from authenticated /core-sync/status. Missing server data is shown as DATA ERROR instead of zero telemetry.</div></div>'+window.renderCoreSide('THIS DEVICE JANUS · LIVE',local,true)+(hasServer?window.renderCoreSide(serverTitle,gr,false):'<div class=\\\"card\\\"><b>'+serverTitle+'</b><div class=\\\"small\\\">Authenticated server request returned no core map. Raw keys: '+esc(Object.keys(gr).join(', ')||'none')+'</div></div>')+'<div class=\\\"card\\\"><b>Connection</b><div class=\\\"small\\\">authenticated device clients online '+esc(online)+' · registered '+esc(registered)+'</div></div>';"

if old_full in s:
    s = s.replace(old_full, new_full)
elif "var raw=await api('GET','/core-sync/status')" not in s:
    prefix = "var envelope=await api('GET','/desktop/runtime-cores?username='+encodeURIComponent(profile));var gr=envelope.runtime||{};var presence=envelope.presence||{};var online=Number(presence.online||gr.remote_clients||0);"
    replacement = "var raw=await api('GET','/core-sync/status');if(typeof raw==='string'){try{raw=JSON.parse(raw);}catch(_){raw={};}}var gr=(raw&&raw.runtime)?raw.runtime:raw;if(!gr||typeof gr!=='object')gr={};var presence={online:Number(gr.remote_clients||0),registered:Number(gr.registered_clients||0)};var online=presence.online;"
    if prefix in s:
        s = s.replace(prefix, replacement)

for v in ('0.60','0.61','0.62'):
    s = s.replace(f'LIVE LOCAL JANUS · v{v}', 'LIVE LOCAL JANUS · v0.63')
p.write_text(s, encoding='utf-8')

html = Path('android/app/src/main/assets/index.html')
h = html.read_text(encoding='utf-8')
for v in ('0.59','0.60','0.61','0.62'):
    h = h.replace(f'LIVE LOCAL JANUS · v{v}', 'LIVE LOCAL JANUS · v0.63')
    h = h.replace(f"client_version:'{v}'", "client_version:'0.63'")
html.write_text(h, encoding='utf-8')

runtime = Path('android/app/src/main/java/com/vardath/janus/JanusLocalCoreRuntime.java')
r = runtime.read_text(encoding='utf-8')
for v in ('0.56','0.57','0.58','0.59','0.60','0.61','0.62'):
    r = r.replace(f'\"client_version\",\"{v}\"', '\"client_version\",\"0.63\"')
runtime.write_text(r, encoding='utf-8')

print('Patched Android v0.63: resilient direct core-sync status + truthful version labels')
