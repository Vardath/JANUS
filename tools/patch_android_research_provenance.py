from pathlib import Path

html = Path('android/app/src/main/assets/index.html')
h = html.read_text(encoding='utf-8')


def replace_once(old: str, new: str):
    global h
    if old not in h:
        raise SystemExit('Android research provenance patch pattern missing: ' + old[:140])
    h = h.replace(old, new, 1)

maintenance_btn = '<button onclick="show(\'maintenance\');refreshMaintenanceReview()"><b>Maintenance review</b><br><span class="small">Quarterly upgrade/security proposals — owner approval required before manual work</span></button>'
provenance_btn = maintenance_btn + '<button onclick="show(\'provenance\');refreshResearchProvenance()"><b>Background research</b><br><span class="small">What JANUS researched, sources used, suppressed work and estimated external-compute cost</span></button>'
replace_once(maintenance_btn, provenance_btn)

settings_view = '<div id="settings" class="view"><button class="action secondary" onclick="show(\'options\')">← Options</button><h2>Settings</h2>'
provenance_view = '''<div id="provenance" class="view"><button class="action secondary" onclick="show('options')">← Options</button><h2>Background research</h2><p class="small">A readable provenance view of JANUS's externalized autonomous research. It shows completed searches, cited sources, usefulness suppression and estimated external-compute usage. It does not expose private chain-of-thought.</p><div style="display:flex;gap:7px;flex-wrap:wrap;margin:10px 0"><button class="action secondary" onclick="refreshResearchProvenance()">Refresh</button></div><div id="provenanceSummary"><div class="card">Loading background research provenance…</div></div><div id="provenanceList"></div></div>\n''' + settings_view
replace_once(settings_view, provenance_view)

old_all = "const main=['chat','messages','observe','options'],all=[...main,'cores','memory','activity','artifacts','research','maintenance','settings'];"
new_all = "const main=['chat','messages','observe','options'],all=[...main,'cores','memory','activity','artifacts','research','maintenance','provenance','settings'];"
replace_once(old_all, new_all)

js = r'''
function provenanceSources(sources){
  if(!Array.isArray(sources)||!sources.length)return '<div class="small">No external source URL was recorded for this item.</div>';
  return '<div style="margin-top:7px">'+sources.map(s=>'<div class="small">Source: '+esc(s.title||'Source')+' — '+esc(s.url||'')+'</div>').join('')+'</div>';
}
function renderResearchProvenance(data){
  let summary=document.getElementById('provenanceSummary'), host=document.getElementById('provenanceList'); if(!host)return;
  let u=data.usefulness||{}, c=data.external_compute||{}, searches=Array.isArray(data.recent_searches)?data.recent_searches:[], gates=Array.isArray(u.recent_gate_decisions)?u.recent_gate_decisions:[];
  if(summary)summary.innerHTML='<div class="card"><b>Background research status</b><div class="small">Useful completed work: '+Number(u.useful||0)+' / '+Number(u.completed_scored||0)+' · usefulness rate '+Math.round(Number(u.usefulness_rate||0)*100)+'%</div><div class="small">Estimated background external compute today: $'+Number(c.background_today_estimated_usd||0).toFixed(4)+' of $'+Number(c.background_daily_limit_usd||0).toFixed(2)+' daily background budget</div><div class="small">Denied by cost governor today: '+Number(c.denied_today||0)+' · background image generation: disabled</div><div class="small">Costs are planning estimates, not provider invoices.</div></div>';
  let suppressed=gates.filter(x=>String(x.decision)==='suppress').slice(0,8);
  let suppressedHtml=suppressed.length?'<div class="card"><b>Recently suppressed before spending API budget</b>'+suppressed.map(x=>'<div class="small" style="margin-top:7px">'+esc(x.topic||'candidate')+' — '+esc((x.reasons||[]).join(', ')||'usefulness gate')+'</div>').join('')+'</div>':'';
  let searchHtml=searches.length?searches.map(x=>'<div class="card"><div class="small">'+esc(x.core_name||'core')+' · '+esc(x.mode||'research')+' · '+esc(x.status||'unknown')+' · '+esc(fmt(x.completed_at||x.created_at))+'</div><h3>'+esc(x.query||'Background research')+'</h3><p>'+esc(x.result_preview||'No result summary recorded.')+'</p><div class="small">Sources recorded: '+Number(x.source_count||0)+'</div>'+provenanceSources(x.sources)+'</div>').join(''):'<div class="card"><b>No completed background research recorded yet</b><p class="small">JANUS may legitimately remain quiet when usefulness, repetition or cost gates suppress work.</p></div>';
  host.innerHTML=suppressedHtml+searchHtml;
}
async function refreshResearchProvenance(){
  let host=document.getElementById('provenanceList'); if(host)host.innerHTML='<div class="card">Refreshing provenance…</div>';
  try{let r=await api('GET','/research-provenance/status');renderResearchProvenance(r)}
  catch(e){if(host)host.innerHTML='<div class="card"><b>Background research provenance unavailable</b><p>'+esc(e.message)+'</p></div>'}
}
'''
replace_once('</script>', js + '\n</script>')

html.write_text(h, encoding='utf-8')
print('Applied Android background research provenance UI patch')
