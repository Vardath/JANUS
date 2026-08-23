from pathlib import Path

html = Path('android/app/src/main/assets/index.html')
h = html.read_text(encoding='utf-8')


def replace_once(old: str, new: str):
    global h
    if old not in h:
        raise SystemExit('Android artifacts patch pattern missing: ' + old[:100])
    h = h.replace(old, new, 1)

activity_btn = '<button onclick="showSub(\'activity\')"><b>Activity</b><br><span class="small">Conversation, reflections, decisions and events</span></button>'
artifact_btn = activity_btn + '<button onclick="show(\'artifacts\');refreshArtifacts()"><b>Artifacts</b><br><span class="small">Continuity reports, research digests, project snapshots and working notes</span></button>'
replace_once(activity_btn, artifact_btn)

settings_view = '<div id="settings" class="view"><button class="action secondary" onclick="show(\'options\')">← Options</button><h2>Settings</h2>'
artifact_view = '''<div id="artifacts" class="view"><button class="action secondary" onclick="show('options')">← Options</button><h2>Artifacts</h2><p class="small">Account-bound reports and working documents created by JANUS. These are externalized artifacts, not hidden chain-of-thought.</p><div class="card"><b>Create artifact</b><div style="display:flex;gap:7px;flex-wrap:wrap;margin-top:9px"><button class="action secondary" onclick="createArtifact('continuity_report')">Continuity report</button><button class="action secondary" onclick="createArtifact('research_digest')">Research digest</button></div><p class="small">Project snapshots remain available through tracked research items; working notes can be created from Chat.</p></div><button class="action secondary" onclick="refreshArtifacts()">Refresh</button><div id="artifactList"><div class="card">Loading artifacts…</div></div></div>\n''' + settings_view
replace_once(settings_view, artifact_view)

old_all = "const main=['chat','messages','observe','options'],all=[...main,'cores','memory','activity','settings'];"
new_all = "const main=['chat','messages','observe','options'],all=[...main,'cores','memory','activity','artifacts','settings'];"
replace_once(old_all, new_all)

js = r'''
function artifactKindLabel(k){return String(k||'artifact').replaceAll('_',' ')}
async function refreshArtifacts(){
  let host=document.getElementById('artifactList'); if(!host)return;
  host.innerHTML='<div class="card">Refreshing artifacts…</div>';
  try{
    let r=await api('GET','/artifacts'); let items=Array.isArray(r.items)?r.items:[];
    if(!items.length){host.innerHTML='<div class="card"><b>No generated artifacts yet</b><p class="small">Create a continuity report or research digest above.</p></div>';return}
    host.innerHTML=items.map(a=>{
      let created=a.created_at?new Date(Number(a.created_at)*1000).toLocaleString():'';
      let availability=a.available?'available':'source file unavailable';
      return '<div class="card"><b>'+esc(a.title||artifactKindLabel(a.kind))+'</b><div class="small">'+esc(artifactKindLabel(a.kind))+' · '+esc(created)+' · '+esc(availability)+'</div><div style="display:flex;gap:7px;flex-wrap:wrap;margin-top:9px"><button class="action secondary" onclick="openArtifact('+Number(a.id)+')">Open</button><button class="action secondary" onclick="useArtifactInChat('+Number(a.id)+')">Use in Chat</button></div></div>';
    }).join('');
  }catch(e){host.innerHTML='<div class="card"><b>Artifacts unavailable</b><p>'+esc(e.message)+'</p></div>'}
}
async function createArtifact(kind){
  setStatus('Creating artifact');
  try{let r=await api('POST','/artifacts',{kind:kind});let a=r.artifact||{};setStatus('Artifact created');await refreshArtifacts();if(a.id)await openArtifact(a.id)}
  catch(e){setStatus('Interface active');alert('Artifact creation failed. '+e.message)}
}
async function openArtifact(id){
  let host=document.getElementById('artifactList');
  try{let r=await api('GET','/artifacts/'+encodeURIComponent(id));let a=r.artifact||{};let p=a.provenance||{};let detail='<div class="card"><button class="action secondary" onclick="refreshArtifacts()">← Artifact list</button><h3>'+esc(a.title||artifactKindLabel(a.kind))+'</h3><p><b>Type:</b> '+esc(artifactKindLabel(a.kind))+'</p><p><b>File:</b> '+esc(a.original_name||'unavailable')+'</p><p><b>Size:</b> '+esc(a.size_bytes||0)+' bytes</p><p><b>Available:</b> '+esc(a.available?'yes':'no')+'</p><details><summary>Provenance</summary><pre class="technical">'+esc(JSON.stringify(p,null,2))+'</pre></details><div style="display:flex;gap:7px;flex-wrap:wrap;margin-top:10px"><button class="action" onclick="useArtifactInChat('+Number(a.id)+')">Use in Chat</button></div><p class="small">The server keeps the underlying file account-bound and indexed for later grounding. Native export/share is a separate Android hardening step.</p></div>';host.innerHTML=detail}
  catch(e){host.innerHTML='<div class="card"><b>Unable to open artifact</b><p>'+esc(e.message)+'</p><button class="action secondary" onclick="refreshArtifacts()">Back</button></div>'}
}
async function useArtifactInChat(id){
  try{let r=await api('GET','/artifacts/'+encodeURIComponent(id));let a=r.artifact||{};let fileId=a.file_id||'';if(!fileId)throw new Error('Artifact file is unavailable.');show('chat');composer.value='Please review and use this JANUS artifact in our current discussion.';pendingAttachments=(typeof pendingAttachments!=='undefined'?pendingAttachments:[]);pendingAttachments.push({id:fileId,filename:a.original_name||a.title||'JANUS artifact'});if(typeof renderAttachments==='function')renderAttachments();composer.focus()}
  catch(e){alert('Could not attach artifact to Chat. '+e.message)}
}
'''
replace_once('</script>', js + '\n</script>')

html.write_text(h, encoding='utf-8')
print('Applied Android generated-artifact workflow patch')
