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
  function localRows(){try{
    let r=JSON.parse(Android.localCoreStatus()||'{}'),states=stateMap(),rows=[];
    for(let x of (r.observe_events||[])){
      if(String(x.core_name||'')!=='interface'||String(x.event_type||'')!=='process_note')continue;
      let raw=String(x.raw_detail||x.detail||''),low=raw.toLowerCase();
      if(!low.includes('autonomous')&&!low.includes('self-assessment')&&!low.includes('self_assessment'))continue;
      let key=String(x.event_id||x.created_at||('i'+rows.length)),state=states[key]||'unread'; if(state==='dismissed')continue;
      let at=x.created_at;if(typeof at==='number'||/^\d+$/.test(String(at||''))){try{at=new Date(Number(at)).toISOString()}catch(e){}}
      rows.push({id:'local:'+key,local:true,local_key:key,state:state,message_type:'Observation',created_at:String(at||''),source:'this device',detail:friendlyThought({core_name:'interface',event_type:'process_note',detail:x.detail||'',raw_detail:raw})});
    }
    rows.sort((a,b)=>String(b.created_at).localeCompare(String(a.created_at)));let seen=new Set(),out=[];
    for(let x of rows){let sig=String(x.detail||'').trim().toLowerCase();if(!sig||seen.has(sig))continue;seen.add(sig);out.push(x);if(out.length>=20)break}return out;
  }catch(e){return []}}
  window.localSetMsg=function(key,state){let m=stateMap();m[String(key)]=state;saveState(m);refresh('messages')};
  window.localAnswer=function(key){let x=(window.messageRows||[]).find(y=>y.local&&y.local_key===String(key));if(!x)return;localSetMsg(key,'read');composer.value=`Regarding your local ${x.message_type||'message'} from ${fmt(x.created_at)}:\n“${String(x.detail||'').slice(0,500)}”\n\n`;show('chat');composer.focus()};
  function renderMergedMessages(serverRows,serverUnread){serverRows=Array.isArray(serverRows)?serverRows:[];let serverText=new Set(serverRows.map(x=>String(x.detail||'').trim().toLowerCase())),locals=localRows().filter(x=>!serverText.has(String(x.detail||'').trim().toLowerCase()));let rows=[...locals,...serverRows].sort((a,b)=>String(b.created_at||'').localeCompare(String(a.created_at||'')));window.messageRows=rows;setBadges(Number(serverUnread||0)+locals.filter(x=>x.state==='unread').length);messageList.innerHTML=rows.map(x=>x.local?`<div class="card"><b>${x.state==='unread'?'New · ':''}${esc(x.message_type||'Observation')}</b><div class="small">${fmt(x.created_at)} · this device</div><p>${esc(x.detail||'')}</p><button class="action" onclick="localAnswer('${esc(x.local_key)}')">Answer in Chat</button> <button class="action secondary" onclick="localSetMsg('${esc(x.local_key)}','read')">Read</button> <button class="action secondary" onclick="localSetMsg('${esc(x.local_key)}','dismissed')">Dismiss</button></div>`:`<div class="card"><b>${x.state==='unread'?'New · ':''}${esc(x.message_type||'Follow-up')}</b><div class="small">${fmt(x.created_at)}</div><p>${esc(x.detail||'')}</p><button class="action" onclick="answerInChat(${x.id})">Answer in Chat</button> <button class="action secondary" onclick="setMsg(${x.id},'read')">Read</button> <button class="action secondary" onclick="setMsg(${x.id},'dismissed')">Dismiss</button></div>`).join('')||'<p>No JANUS messages yet.</p>'}
  if(window.refresh&&!window.__janusLocalOutboxRefreshWrapped){window.__janusLocalOutboxRefreshWrapped=true;let oldRefresh=window.refresh;window.refresh=async function(p){if(p!=='messages')return oldRefresh(p);let before=(window.messageRows||[]).slice(),serverUnread=0;try{let r=await api('GET','/desktop/messages?username='+encodeURIComponent(profile));before=r.items||[];serverUnread=Number(r.unread||0)}catch(e){setStatus('Offline · local runtime available')}renderMergedMessages(before,serverUnread)}};
})();
'''
if '__janusLocalOutboxInstalled' not in s:
    if marker not in s: raise SystemExit('Local outbox insertion point not found')
    s=s.replace(marker,block+'\n'+marker,1);p.write_text(s,encoding='utf-8')
print('Device-local Interface outbox verified')