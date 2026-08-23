from pathlib import Path

html = Path('android/app/src/main/assets/index.html')
h = html.read_text(encoding='utf-8')


def replace_once(old: str, new: str):
    global h
    if old not in h:
        raise SystemExit('Android research workspace patch pattern missing: ' + old[:120])
    h = h.replace(old, new, 1)

artifact_btn = '<button onclick="show(\'artifacts\');refreshArtifacts()"><b>Artifacts</b><br><span class="small">Continuity reports, research digests, project snapshots and working notes</span></button>'
research_btn = artifact_btn + '<button onclick="show(\'research\');refreshResearchWorkspace()"><b>Research workspace</b><br><span class="small">Established results, hypotheses, negative results, evidence, open questions and proposed tests</span></button>'
replace_once(artifact_btn, research_btn)

settings_view = '<div id="settings" class="view"><button class="action secondary" onclick="show(\'options\')">← Options</button><h2>Settings</h2>'
research_view = '''<div id="research" class="view"><button class="action secondary" onclick="show('options')">← Options</button><h2>Research workspace</h2><p class="small">JANUS keeps mathematical results, physical interpretations, hypotheses, failed tests and open work explicitly separated. Negative results remain visible rather than being discarded.</p><div class="card"><b>Workspace controls</b><div style="display:flex;gap:7px;flex-wrap:wrap;margin-top:9px"><button class="action secondary" onclick="seedResearchWorkspace()">Load JANUS research baseline</button><button class="action secondary" onclick="refreshResearchWorkspace()">Refresh</button></div><p class="small">Loading the baseline is idempotent and account-scoped. It does not promote hypotheses to established results.</p></div><div id="researchFilters" style="display:flex;gap:6px;flex-wrap:wrap;margin:10px 0"><button class="action secondary" onclick="setResearchFilter('all')">All</button><button class="action secondary" onclick="setResearchFilter('established')">Established</button><button class="action secondary" onclick="setResearchFilter('hypotheses')">Hypotheses</button><button class="action secondary" onclick="setResearchFilter('negative')">Negative results</button><button class="action secondary" onclick="setResearchFilter('open')">Open questions</button><button class="action secondary" onclick="setResearchFilter('tests')">Proposed tests</button></div><div id="researchSummary"></div><div id="researchList"><div class="card">Loading research workspace…</div></div></div>\n''' + settings_view
replace_once(settings_view, research_view)

old_all = "const main=['chat','messages','observe','options'],all=[...main,'cores','memory','activity','artifacts','settings'];"
new_all = "const main=['chat','messages','observe','options'],all=[...main,'cores','memory','activity','artifacts','research','settings'];"
replace_once(old_all, new_all)

js = r'''
let researchClaims=[], researchFilter='all';
function researchStateLabel(s){return String(s||'unknown').replaceAll('_',' ')}
function researchKindLabel(k){return String(k||'claim').replaceAll('_',' ')}
function researchGroup(c){
  let k=String(c.claim_kind||''), s=String(c.epistemic_state||'');
  if(k==='negative_result'||['closed_negative','contradicted','falsified'].includes(s))return 'negative';
  if(k==='open_question'||s==='open')return 'open';
  if(k==='proposed_test')return 'tests';
  if(k==='hypothesis'||k==='interpretation'||['provisional','untested','inconclusive'].includes(s))return 'hypotheses';
  if(['theorem','definition','derivation','empirical_finding','boundary'].includes(k)&&['established','audited','supported'].includes(s))return 'established';
  return 'other';
}
function setResearchFilter(f){researchFilter=f;renderResearchWorkspace()}
function researchCounts(items){let out={established:0,hypotheses:0,negative:0,open:0,tests:0,other:0};items.forEach(c=>out[researchGroup(c)]++);return out}
function renderResearchWorkspace(){
  let host=document.getElementById('researchList'), summary=document.getElementById('researchSummary'); if(!host)return;
  let counts=researchCounts(researchClaims);
  if(summary)summary.innerHTML='<div class="card"><b>'+researchClaims.length+' research records</b><div class="small">'+counts.established+' established/audited · '+counts.hypotheses+' hypotheses/provisional · '+counts.negative+' negative · '+counts.open+' open questions · '+counts.tests+' proposed tests</div></div>';
  let items=researchClaims.filter(c=>researchFilter==='all'||researchGroup(c)===researchFilter);
  if(!items.length){host.innerHTML='<div class="card"><b>No records in this view</b><p class="small">Refresh the workspace or load the JANUS research baseline.</p></div>';return}
  host.innerHTML=items.map(c=>{
    let tags=Array.isArray(c.tags)&&c.tags.length?'<div class="small">Tags: '+esc(c.tags.join(', '))+'</div>':'';
    let boundary=researchGroup(c)==='negative'?'<div class="small"><b>Retained negative result</b> — this remains part of the research record.</div>':'';
    return '<div class="card"><div class="small">'+esc(researchKindLabel(c.claim_kind))+' · '+esc(researchStateLabel(c.epistemic_state))+' · '+esc(c.domain||'general')+'</div><h3>'+esc(c.title||'Untitled research item')+'</h3><p>'+esc(c.statement||'')+'</p>'+boundary+tags+'<div style="display:flex;gap:7px;flex-wrap:wrap;margin-top:9px"><button class="action secondary" onclick="useResearchInChat('+Number(c.id)+')">Discuss in Chat</button><button class="action secondary" onclick="showResearchEvidence('+Number(c.id)+')">Evidence</button></div><div id="researchEvidence'+Number(c.id)+'"></div></div>';
  }).join('');
}
async function refreshResearchWorkspace(){
  let host=document.getElementById('researchList'); if(!host)return;
  host.innerHTML='<div class="card">Refreshing research workspace…</div>';
  try{
    let r=await api('GET','/research/workspace');
    researchClaims=Array.isArray(r.claims)?r.claims:(Array.isArray(r.items)?r.items:[]);
    renderResearchWorkspace();
  }catch(e){host.innerHTML='<div class="card"><b>Research workspace unavailable</b><p>'+esc(e.message)+'</p><p class="small">JANUS Chat remains available; this screen is a view of the durable research ledger.</p></div>'}
}
async function seedResearchWorkspace(){
  setStatus('Loading research baseline');
  try{let r=await api('POST','/research/workspace/seed',{});setStatus('Research workspace ready');await refreshResearchWorkspace();}
  catch(e){setStatus('Interface active');alert('Could not load research baseline. '+e.message)}
}
function findResearchClaim(id){return researchClaims.find(c=>Number(c.id)===Number(id))}
function useResearchInChat(id){
  let c=findResearchClaim(id); if(!c)return;
  show('chat');
  composer.value='Please continue our research on "'+String(c.title||'this item').replaceAll('"','')+'". Preserve its current epistemic status ('+researchStateLabel(c.epistemic_state)+') and distinguish established evidence from interpretation.';
  composer.focus();
}
function showResearchEvidence(id){
  let c=findResearchClaim(id), host=document.getElementById('researchEvidence'+Number(id)); if(!host||!c)return;
  let ev=Array.isArray(c.evidence)?c.evidence:[];
  if(!ev.length){host.innerHTML='<div class="small" style="margin-top:9px">No evidence entries included in this workspace summary. Evidence can be added through JANUS research work without automatically changing the claim status.</div>';return}
  host.innerHTML='<div style="margin-top:9px">'+ev.map(e=>'<div class="small"><b>'+esc(researchKindLabel(e.evidence_kind))+'</b>: '+esc(e.summary||'')+(e.result?' — '+esc(e.result):'')+'</div>').join('')+'</div>';
}
'''
replace_once('</script>', js + '\n</script>')

html.write_text(h, encoding='utf-8')
print('Applied Android research workspace UI patch')
