from pathlib import Path

p=Path('android/app/src/main/assets/index.html')
s=p.read_text(encoding='utf-8')
marker='</script></body></html>'
block=r'''
(function(){
  if(window.__janusLocalOutboxInstalled)return;
  window.__janusLocalOutboxInstalled=true;
  function stateMap(){try{return JSON.parse(localStorage.janusLocalMessageState||'{}')||{}}catch(e){return {}}}
  function saveState(m){try{localStorage.janusLocalMessageState=JSON.stringify(m)}catch(e){}}
  function lowValueText(text){let t=String(text||'').toLowerCase();return !t||t.includes('self-assessment')||t.includes('self_assessment')||t.includes('active fano direction')||t.includes('fano d')||t.includes('processed 0 peer inputs')||t.includes('processed 1 peer inputs')||t.includes('interface updated the user-facing shared state')||t.includes('interface formulated the shared state around')||t.includes('integration: combine hemispheres')||t.includes('autonomous boundary task')||t.includes('maintenance pass')}
  function messageWorthy(text){let t=String(text||'').toLowerCase();if(lowValueText(t))return false;return t.includes('?')||t.includes('conclusion')||t.includes('found ')||t.includes('discovered')||t.includes('new connection')||t.includes('new finding')||t.includes('unresolved question')||t.includes('needs your input')||t.includes('recommend')||t.includes('warning')||t.includes('important')}
  function canonical(text){return String(text||'').toLowerCase().replace(/\d+(?:\.\d+)?/g,'#').replace(/[^a-z?#]+/g,' ').replace(/\s+/g,' ').trim()}
  function visibleServerRow(x){if(String(x&&x.message_type||'').toLowerCase()==='question')return true;return !lowValueText(x&&x.detail||'')}
  function localRows(){try{let r=JSON.parse(Android.localCoreStatus()||'{}'),states=stateMap(),rows=[];for(let x of (r.observe_events||[])){if(String(x.core_name||'')!=='interface'||String(x.event_type||'')!=='process_note')continue;let raw=String(x.raw_detail||x.detail||''),low=raw.toLowerCase();if(!low.includes('autonomous')||!messageWorthy(raw))continue;let detail=friendlyThought({core_name:'interface',event_type:'process_note',detail:x.detail||'',raw_detail:raw});if(!messageWorthy(detail)&&!messageWorthy(raw))continue;let key=String(x.event_id||x.created_at||('i'+rows.length)),state=states[key]||'unread';if(state==='dismissed')continue;let at=x.created_at;if(typeof at==='number'||/^\d+$/.test(String(at||''))){try{at=new Date(Number(at)).toISOString()}catch(e){}}rows.push({id:'local:'+key,local:true,local_key:key,state,message_type:raw.includes('?')?'Question':'Observation',created_at:String(at||''),source:'this device',detail})}rows.sort((a,b)=>String(b.created_at).localeCompare(String(a.created_at)));let seen=new Set(),out=[];for(let x of rows){let sig=canonical(x.detail);if(!sig||seen.has(sig))continue;seen.add(sig);out.push(x);if(out.length>=10)break}return out}catch(e){return []}}
  window.localSetMsg=function(key,state){let m=stateMap();m[String(key)]=state;saveState(m);window.refresh('messages')};
  window.localAnswer=function(key){let x=(window.messageRows||[]).find(y=>y.local&&y.local_key===String(key));if(!x)return;localSetMsg(key,'read');composer.value=`Regarding your local ${x.message_type||'message'} from ${fmt(x.created_at)}:\n“${String(x.detail||'').slice(0,500)}”\n\n`;show('chat');composer.focus()};
  function renderMergedMessages(serverRows){serverRows=(Array.isArray(serverRows)?serverRows:[]).filter(visibleServerRow);let serverText=new Set(serverRows.map(x=>canonical(x.detail))),locals=localRows().filter(x=>!serverText.has(canonical(x.detail)));let rows=[...locals,...serverRows].sort((a,b)=>String(b.created_at||'').localeCompare(String(a.created_at||''))),seen=new Set();rows=rows.filter(x=>{let k=canonical(x.detail);if(!k||seen.has(k))return false;seen.add(k);return true});window.messageRows=rows;setBadges(rows.filter(x=>x.state==='unread').length);messageList.innerHTML=rows.map(x=>x.local?`<div class="card"><b>${x.state==='unread'?'New · ':''}${esc(x.message_type||'Observation')}</b><div class="small">${fmt(x.created_at)} · this device</div><p>${esc(x.detail||'')}</p><button class="action" onclick="localAnswer('${esc(x.local_key)}')">Answer in Chat</button> <button class="action secondary" onclick="localSetMsg('${esc(x.local_key)}','read')">Read</button> <button class="action secondary" onclick="localSetMsg('${esc(x.local_key)}','dismissed')">Dismiss</button></div>`:`<div class="card"><b>${x.state==='unread'?'New · ':''}${esc(x.message_type||'Follow-up')}</b><div class="small">${fmt(x.created_at)}</div><p>${esc(x.detail||'')}</p><button class="action" onclick="answerInChat(${x.id})">Answer in Chat</button> <button class="action secondary" onclick="setMsg(${x.id},'read')">Read</button> <button class="action secondary" onclick="setMsg(${x.id},'dismissed')">Dismiss</button></div>`).join('')||'<p>No JANUS messages yet.</p>'}
  let oldRefresh=window.refresh;
  window.refresh=async function(p){if(p!=='messages')return oldRefresh(p);let server=[];try{let r=await api('GET','/desktop/messages?username='+encodeURIComponent(profile));server=r.items||[]}catch(e){setStatus('Offline · local runtime available')}renderMergedMessages(server)};
  /* Global function bindings in Android WebView can retain the original refresh function.
     Rebind navigation and polling explicitly so opening Messages cannot replace the local
     outbox with the server-only list and reset the visible badge. */
  window.show=function(p){all.forEach(x=>document.getElementById(x).classList.toggle('active',x===p));main.forEach(x=>document.getElementById('n-'+x).classList.toggle('on',x===p||(x==='options'&&!main.includes(p))));if(p!=='chat')window.refresh(p)};
  window.showSub=function(p){window.show(p)};
  window.schedule=function(){if(timer)clearInterval(timer);if(autoRefresh.checked)timer=setInterval(()=>{let p=all.find(x=>document.getElementById(x).classList.contains('active'));if(['messages','observe','options','activity','memory','cores'].includes(p))window.refresh(p);else window.refresh('messages')},Number(refreshSeconds.value)*1000)};
})();
'''
if '__janusLocalOutboxInstalled' not in s:
    if marker not in s: raise SystemExit('Local outbox insertion point not found')
    s=s.replace(marker,block+'\n'+marker,1)
    p.write_text(s,encoding='utf-8')
print('Device-local Interface outbox verified; navigation uses merged refresh')