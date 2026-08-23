from pathlib import Path

html = Path('android/app/src/main/assets/index.html')
h = html.read_text(encoding='utf-8')


def replace_once(old: str, new: str):
    global h
    if old not in h:
        raise SystemExit('Android protocol capability patch pattern missing: ' + old[:160])
    h = h.replace(old, new, 1)

provenance_btn = '<button onclick="show(\'provenance\');refreshResearchProvenance()"><b>Background research</b><br><span class="small">What JANUS researched, sources used, suppressed work and estimated external-compute cost</span></button>'
compat_btn = provenance_btn + '<button onclick="show(\'compatibility\');refreshCompatibility()"><b>Compatibility</b><br><span class="small">Server protocol, deployed capabilities and client compatibility</span></button>'
replace_once(provenance_btn, compat_btn)

settings_view = '<div id="settings" class="view"><button class="action secondary" onclick="show(\'options\')">← Options</button><h2>Settings</h2>'
compat_view = '''<div id="compatibility" class="view"><button class="action secondary" onclick="show('options')">← Options</button><h2>Compatibility</h2><p class="small">JANUS asks the deployed server what it actually supports before treating optional workflows as available.</p><div style="display:flex;gap:7px;flex-wrap:wrap;margin:10px 0"><button class="action secondary" onclick="refreshCompatibility()">Refresh</button></div><div id="compatibilitySummary"><div class="card">Checking server capabilities…</div></div><div id="compatibilityFeatures"></div></div>\n''' + settings_view
replace_once(settings_view, compat_view)

old_all = "const main=['chat','messages','observe','options'],all=[...main,'cores','memory','activity','artifacts','research','maintenance','provenance','settings'];"
new_all = "const main=['chat','messages','observe','options'],all=[...main,'cores','memory','activity','artifacts','research','maintenance','provenance','compatibility','settings'];"
replace_once(old_all, new_all)

js = r'''
let janusCapabilities=null;
function capabilityLabel(k){return String(k||'').replaceAll('_',' ')}
function capabilityAvailable(name){return !!(janusCapabilities&&janusCapabilities.features&&janusCapabilities.features[name])}
function renderCompatibility(data){
  janusCapabilities=data||null;
  let summary=document.getElementById('compatibilitySummary'), host=document.getElementById('compatibilityFeatures'); if(!host)return;
  let a=(data&&data.clients&&data.clients.android)||{}, protocol=Number(data&&data.protocol_version||0), features=(data&&data.features)||{};
  let appVersion='0.69';
  let min=String(a.minimum_version||'unknown'), rec=String(a.recommended_version||min), commit=String(data&&data.deployed_commit||'unknown');
  let ok=protocol>=1;
  if(summary)summary.innerHTML='<div class="card"><b>'+(ok?'Protocol compatible':'Protocol compatibility unknown')+'</b><div class="small">Server protocol: '+protocol+' · Android app: '+esc(appVersion)+'</div><div class="small">Minimum Android: '+esc(min)+' · recommended: '+esc(rec)+'</div><div class="small">Deployed server commit: '+esc(commit)+'</div></div>';
  let names=Object.keys(features).sort();
  host.innerHTML='<div class="card"><b>Server capabilities</b>'+names.map(k=>'<div class="small" style="margin-top:6px">'+(features[k]?'✓':'—')+' '+esc(capabilityLabel(k))+'</div>').join('')+'</div>';
  applyCapabilityVisibility();
}
function applyCapabilityVisibility(){
  if(!janusCapabilities||!janusCapabilities.features)return;
  let map={
    "Research workspace":"research_workspace",
    "Maintenance review":"maintenance_review",
    "Background research":"research_provenance",
    "Artifacts":"artifact_workspace"
  };
  document.querySelectorAll('#options .options button').forEach(btn=>{
    let title=(btn.querySelector('b')||{}).textContent||'';
    let cap=map[title]; if(!cap)return;
    let available=capabilityAvailable(cap);
    btn.disabled=!available;
    btn.style.opacity=available?'1':'0.55';
    btn.title=available?'':'This deployed server does not advertise '+capabilityLabel(cap)+'.';
  });
}
async function refreshCompatibility(){
  let host=document.getElementById('compatibilityFeatures'); if(host)host.innerHTML='<div class="card">Checking server protocol…</div>';
  try{let r=await api('GET','/protocol/capabilities',{},false);renderCompatibility(r)}
  catch(e){janusCapabilities=null;if(host)host.innerHTML='<div class="card"><b>Capability negotiation unavailable</b><p>'+esc(e.message)+'</p><p class="small">JANUS will keep optional features conservative rather than pretending they are supported.</p></div>'}
}
'''
replace_once('</script>', js + '\n</script>')

# Refresh capability knowledge after an authenticated session becomes active without
# making login depend on negotiation succeeding.
needle = "profileLabel.textContent='Signed in as '+profile;login.classList.add('hidden');"
if needle in h and "refreshCompatibility().catch" not in h:
    h = h.replace(needle, needle + "refreshCompatibility().catch(()=>{});", 1)

html.write_text(h, encoding='utf-8')
print('Applied Android protocol/capability negotiation UI patch')
