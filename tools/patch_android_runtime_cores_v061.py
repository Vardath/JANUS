from pathlib import Path

p = Path('android/app/src/main/java/com/vardath/janus/MainActivity.java')
s = p.read_text(encoding='utf-8')

# This patch runs last. Earlier connectivity patches switched the topology panel to
# /core-sync/status; the UI then kept showing the old zero/unknown fallback even
# while /desktop/runtime-cores and chat could see the live server society.
old = "var gr=await api('GET','/core-sync/status');var connected=Number(gr.remote_clients||0)>0;var title=connected?'Connected · global JANUS':'Reachable · awaiting authenticated heartbeat';host.innerHTML='<div class=\\\"card\\\"><b>JANUS 11-core topology</b><p>7 specialist perspectives feed two hemispheres. The hemispheres feed the consensus reader/giver. Consensus feeds the interface core that represents JANUS to you.</p><div class=\\\"small\\\">The local society runs independently on this device. Global status is only called connected after this account has an authenticated heartbeat.</div></div>'+window.renderCoreSide('This device · local JANUS',local,true)+window.renderCoreSide(title,gr,false);"
new = "var envelope=await api('GET','/desktop/runtime-cores?username='+encodeURIComponent(profile));var gr=envelope.runtime||{};var presence=envelope.presence||{};var online=Number(presence.online||gr.remote_clients||0);var title='SERVER JANUS · LIVE';var list=document.getElementById('coreList');if(list)list.innerHTML='';host.innerHTML='<div class=\\\"card\\\"><b>JANUS 11-core topology</b><p><b>Two independent runtimes are shown below.</b> This device is the local JANUS society. Server JANUS is the persistent online society on Render.</p><div class=\\\"small\\\">Server values come from /desktop/runtime-cores. Local values come directly from this device. Neither substitutes counters for the other.</div></div>'+window.renderCoreSide('THIS DEVICE JANUS · LIVE',local,true)+window.renderCoreSide(title,gr,false)+'<div class=\\\"card\\\"><b>Connection</b><div class=\\\"small\\\">authenticated device clients online '+esc(online)+' · registered '+esc(presence.registered||gr.registered_clients||0)+'</div></div>';"
if old not in s:
    raise SystemExit('post-connectivity refreshCoreTopology block not found')
s = s.replace(old, new)

# Make server/local provenance explicit and avoid truthy/falsy rendering turning
# legitimate numeric zero into an unknown fallback.
s = s.replace("(isLocal?' · sync '+esc(r.sync_state||'unknown'):' · clients '+esc(r.remote_clients||0))", "(isLocal?' · sync '+esc(r.sync_state||'unknown'):' · clients '+esc(Number(r.remote_clients||0)))")

p.write_text(s, encoding='utf-8')
print('Patched Android v0.61: authoritative /desktop/runtime-cores server panel + explicit local/server separation')
