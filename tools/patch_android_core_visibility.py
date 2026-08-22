from pathlib import Path

html = Path('android/app/src/main/assets/index.html')
h = html.read_text(encoding='utf-8')

# v0.59 refreshed the local core panel every two seconds by replacing the entire
# coreTopology host. That briefly erased the separately-fetched online/global
# panel. Leave the Cores page to refreshCoreTopology(), which renders local and
# online JANUS together, and keep the fast local refresh for Options/Observe only.
old = "if(cores&&cores.classList.contains('active')){let host=document.getElementById('coreTopology');if(host){let r=janusLocalSnapshot();host.innerHTML=janusLiveCardHtml()+window.renderCoreSide('This device · local JANUS',r,true);let cl=document.getElementById('coreList');if(cl)cl.innerHTML='';}}"
if old in h:
    h = h.replace(old, "if(cores&&cores.classList.contains('active')&&window.refreshCoreTopology&&!window.__janusCoreTopologyBusy){window.__janusCoreTopologyBusy=true;Promise.resolve(window.refreshCoreTopology()).finally(function(){setTimeout(function(){window.__janusCoreTopologyBusy=false;},750);});}")
else:
    raise SystemExit('v0.59 core refresh block not found')

# Do not hit the server every two seconds. The visible local card can still update
# quickly on Options/Observe; the combined Cores page is refreshed on its normal
# cadence and when opened.
h = h.replace("setInterval(janusRefreshVisibleLocal,2000);", "setInterval(function(){let c=document.getElementById('cores');if(!c||!c.classList.contains('active'))janusRefreshVisibleLocal();},2000);")

# Make the combined topology refresh immediately when the Cores page is opened.
h = h.replace("setTimeout(janusRefreshVisibleLocal,60);return x}}", "setTimeout(janusRefreshVisibleLocal,60);if(p==='cores'&&window.refreshCoreTopology)setTimeout(window.refreshCoreTopology,100);return x}}")

html.write_text(h, encoding='utf-8')
print('Patched Android v0.60: persistent local + online core topology without flicker')
