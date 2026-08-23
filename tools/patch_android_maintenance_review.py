from pathlib import Path

html = Path('android/app/src/main/assets/index.html')
h = html.read_text(encoding='utf-8')


def replace_once(old: str, new: str):
    global h
    if old not in h:
        raise SystemExit('Android maintenance review patch pattern missing: ' + old[:140])
    h = h.replace(old, new, 1)

research_btn = '<button onclick="show(\'research\');refreshResearchWorkspace()"><b>Research workspace</b><br><span class="small">Established results, hypotheses, negative results, evidence, open questions and proposed tests</span></button>'
maintenance_btn = research_btn + '<button onclick="show(\'maintenance\');refreshMaintenanceReview()"><b>Maintenance review</b><br><span class="small">Quarterly upgrade/security proposals — owner approval required before manual work</span></button>'
replace_once(research_btn, maintenance_btn)

settings_view = '<div id="settings" class="view"><button class="action secondary" onclick="show(\'options\')">← Options</button><h2>Settings</h2>'
maintenance_view = '''<div id="maintenance" class="view"><button class="action secondary" onclick="show('options')">← Options</button><h2>Maintenance review</h2><p class="small">JANUS may prepare maintenance and upgrade proposals, but it cannot change code, dependencies, models, configuration or deployments by itself. Approval here means <b>manual work is permitted for review</b>; it does not execute an upgrade.</p><div id="maintenanceSummary"><div class="card">Loading maintenance status…</div></div><div style="display:flex;gap:7px;flex-wrap:wrap;margin:10px 0"><button class="action secondary" onclick="refreshMaintenanceReview()">Refresh</button></div><div id="maintenanceReviews"></div></div>\n''' + settings_view
replace_once(settings_view, maintenance_view)

old_all = "const main=['chat','messages','observe','options'],all=[...main,'cores','memory','activity','artifacts','research','settings'];"
new_all = "const main=['chat','messages','observe','options'],all=[...main,'cores','memory','activity','artifacts','research','maintenance','settings'];"
replace_once(old_all, new_all)

js = r'''
let maintenanceReviews=[];
function maintenanceStateLabel(s){return String(s||'awaiting_owner_review').replaceAll('_',' ')}
function maintenanceDate(v){try{return v?new Date(v).toLocaleString():'Unknown'}catch(e){return String(v||'Unknown')}}
function maintenanceReportLines(report){
  let sections=Array.isArray(report&&report.review_sections)?report.review_sections:[];
  if(!sections.length)return '<div class="small">No detailed maintenance sections were included.</div>';
  return '<div style="margin-top:9px">'+sections.map(s=>'<div class="small"><b>'+esc(s.area||'review')+'</b>: '+esc(s.request||'')+'</div>').join('')+'</div>';
}
function renderMaintenanceReviews(data){
  let summary=document.getElementById('maintenanceSummary'), host=document.getElementById('maintenanceReviews'); if(!host)return;
  let m=(data&&data.maintenance)||{}, last=m.last_review||null;
  if(summary)summary.innerHTML='<div class="card"><b>Quarterly maintenance: '+(m.enabled?'enabled':'unavailable')+'</b><div class="small">Interval: '+esc(String(m.interval_days||90))+' days · '+(m.due?'review due':'not currently due')+'</div><div class="small">Next due: '+esc(maintenanceDate(m.next_due_at))+'</div><div class="small"><b>Automatic changes: disabled</b> · owner approval required</div></div>';
  maintenanceReviews=Array.isArray(data&&data.reviews)?data.reviews:[];
  if(!maintenanceReviews.length){host.innerHTML='<div class="card"><b>No maintenance proposals yet</b><p class="small">JANUS will create one when the scheduled review is due. No action is required now.</p></div>';return}
  host.innerHTML=maintenanceReviews.map(r=>{
    let report=r.report||{}, state=String(r.review_state||report.review_state||'awaiting_owner_review'), pending=state==='awaiting_owner_review';
    let actions=pending?'<div style="display:flex;gap:7px;flex-wrap:wrap;margin-top:10px"><button class="action" onclick="maintenanceDecision('+Number(r.id)+',\'approved_for_manual_work\')">Approve for manual work</button><button class="action secondary" onclick="maintenanceDecision('+Number(r.id)+',\'deferred\')">Defer</button><button class="action secondary" onclick="maintenanceDecision('+Number(r.id)+',\'rejected\')">Reject</button></div>':'<div class="small" style="margin-top:9px">Decision recorded: <b>'+esc(maintenanceStateLabel(state))+'</b>. No automatic changes were made.</div>';
    return '<div class="card"><div class="small">Review #'+Number(r.id)+' · '+esc(maintenanceDate(r.created_at))+'</div><h3>'+esc(String(report.proposal_kind||'Maintenance / upgrade review').replaceAll('_',' '))+'</h3><div class="small">State: <b>'+esc(maintenanceStateLabel(state))+'</b></div><div class="small">Deployed commit at review: '+esc(report.deployed_commit||'unknown')+'</div>'+maintenanceReportLines(report)+'<p class="small"><b>Protected boundary:</b> approval never authorizes JANUS to self-modify or self-deploy.</p>'+actions+'</div>';
  }).join('');
}
async function refreshMaintenanceReview(){
  let host=document.getElementById('maintenanceReviews'); if(host)host.innerHTML='<div class="card">Refreshing maintenance proposals…</div>';
  try{let r=await api('GET','/maintenance/status');renderMaintenanceReviews(r)}
  catch(e){if(host)host.innerHTML='<div class="card"><b>Maintenance review unavailable</b><p>'+esc(e.message)+'</p><p class="small">This screen is restricted to the configured JANUS owner account.</p></div>'}
}
async function maintenanceDecision(id,decision){
  let human=decision==='approved_for_manual_work'?'approve this proposal for manual review/work':decision==='deferred'?'defer this proposal':'reject this proposal';
  if(!confirm('Confirm: '+human+'? JANUS will not make or deploy any changes automatically.'))return;
  try{let r=await api('POST','/maintenance/reviews/'+encodeURIComponent(id)+'/decision',{decision:decision});alert(r.message||'Maintenance decision recorded.');await refreshMaintenanceReview()}
  catch(e){alert('Could not record maintenance decision. '+e.message)}
}
'''
replace_once('</script>', js + '\n</script>')

html.write_text(h, encoding='utf-8')
print('Applied Android maintenance review UI patch')
