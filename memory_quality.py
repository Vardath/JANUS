"""Phase 2 Step 5: memory quality, retrieval and continuity reinforcement.

This layer keeps the existing desktop_memory store intact, but adds deterministic
whole-history retrieval, correction precedence, reflection/ponder markers, exact
repeat consolidation metrics and gentle trace->working->episodic promotion.
It never exposes hidden chain-of-thought; retrieved context is limited to persisted
user-visible conversation/memory records.
"""
from __future__ import annotations

import json, os, re, sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from fastapi import APIRouter, Header
import auth

DB_PATH=Path(os.getenv('JANUS_DB_PATH','/data/janus.sqlite3'))
router=APIRouter(prefix='/memory-quality',tags=['memory-quality'])
WORD=re.compile(r"[A-Za-z][A-Za-z0-9_-]{2,}")
STOP={'the','and','that','this','with','from','have','your','you','are','was','for','but','not','what','when','where','how','why','into','about','then','than','they','them','their','our','out','all','can','will','would','should','could'}
REFLECT=('think about','ponder','mull','mull it over','remember this','keep this in mind','come back to this')
CORRECT=('actually','correction','i mean','not ','rather than','instead','you forgot','that is wrong','that was wrong','don\'t confuse','do not confuse')


def _now(): return datetime.now(timezone.utc).isoformat()
def _db():
    DB_PATH.parent.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(DB_PATH,timeout=10); c.row_factory=sqlite3.Row
    c.execute('''CREATE TABLE IF NOT EXISTS janus_memory_quality(
      id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id TEXT NOT NULL, memory_id INTEGER,
      event_kind TEXT NOT NULL, score REAL NOT NULL DEFAULT 0, detail_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL)''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_memory_quality_profile ON janus_memory_quality(profile_id,id DESC)')
    return c

def _tokens(s:str)->set[str]: return {x.lower() for x in WORD.findall(str(s or '')) if x.lower() not in STOP}
def _sim(a:str,b:str)->float:
    x,y=_tokens(a),_tokens(b)
    return len(x&y)/max(1,len(x|y)) if x and y else 0.0

def _is_reflect(text:str)->bool: return any(p in text.lower() for p in REFLECT)
def _is_correction(text:str)->bool: return any(p in text.lower() for p in CORRECT)

def _record(profile,event,memory_id=None,score=0.0,**detail):
    with _db() as c:
        c.execute('INSERT INTO janus_memory_quality(profile_id,memory_id,event_kind,score,detail_json,created_at) VALUES(?,?,?,?,?,?)',
                  (profile,memory_id,event,float(score),json.dumps(detail,separators=(',',':')), _now()))

def relevant_memories(profile:str, query:str, limit:int=8)->list[dict[str,Any]]:
    """Retrieve from the whole retained history, not just the latest N messages."""
    try:
        with _db() as c:
            rows=c.execute("SELECT id,role,content,level,created_at FROM desktop_memory WHERE profile_id=? AND role IN ('user','assistant','reflection','thread_context') ORDER BY id DESC",(profile,)).fetchall()
    except Exception: return []
    q=_tokens(query); ranked=[]
    for age,r in enumerate(rows):
        text=str(r['content'] or ''); toks=_tokens(text)
        overlap=len(q&toks)/max(1,len(q)) if q else 0.0
        sim=_sim(query,text)
        correction=1.0 if r['role']=='user' and _is_correction(text) else 0.0
        reflect=1.0 if r['role']=='user' and _is_reflect(text) else 0.0
        level={'trace':0.0,'working':0.08,'episodic':0.15,'core':0.25}.get(str(r['level']),0.0)
        recency=max(0.0,0.10-(age*0.001))
        score=max(overlap,sim)+0.20*correction+0.12*reflect+level+recency
        if score>=0.20: ranked.append((score,int(r['id']),dict(r)))
    ranked.sort(key=lambda x:(x[0],x[1]),reverse=True)
    chosen=[]; seen=[]
    for score,mid,r in ranked:
        # exact/near duplicate responses should not crowd out independent history
        if any(_sim(r['content'],x['content'])>=0.92 for x in seen): continue
        r['retrieval_score']=round(score,3); chosen.append(r); seen.append(r)
        if len(chosen)>=max(1,min(limit,16)): break
    return list(reversed(chosen))

def format_context(profile:str, query:str, limit:int=8)->str:
    items=relevant_memories(profile,query,limit)
    if not items: return ''
    lines=['Relevant retained context from across conversation history:']
    for r in items:
        flags=[]
        if r['role']=='user' and _is_correction(r['content']): flags.append('CORRECTION/CLARIFICATION — prefer over earlier conflicting material')
        if r['role']=='user' and _is_reflect(r['content']): flags.append('THREAD TO REMEMBER/REVISIT')
        suffix=(' ['+'; '.join(flags)+']') if flags else ''
        lines.append(f"- {r['role']} ({r['level']}): {r['content']}{suffix}")
    return '\n'.join(lines)

def reinforce_after_turn(profile:str, message:str)->dict[str,Any]:
    """Promote salient user turns gently and record duplicate/correction quality signals."""
    try:
        with _db() as c:
            row=c.execute("SELECT id,level FROM desktop_memory WHERE profile_id=? AND role='user' AND content=? ORDER BY id DESC LIMIT 1",(profile,message)).fetchone()
            if not row: return {'ok':False}
            mid=int(row['id']); old=str(row['level']); target=old
            if _is_correction(message) or _is_reflect(message): target='working' if old=='trace' else ('episodic' if old=='working' else old)
            if len(message)>=240 and old=='trace': target='working'
            if target!=old: c.execute('UPDATE desktop_memory SET level=? WHERE id=? AND profile_id=?',(target,mid,profile))
            dup=int(c.execute("SELECT COUNT(*) FROM desktop_memory WHERE profile_id=? AND role='user' AND lower(trim(content))=lower(trim(?))",(profile,message)).fetchone()[0])
            c.commit()
        _record(profile,'turn_reinforcement',mid,1.0 if target!=old else 0.5,old_level=old,new_level=target,exact_repeat_count=dup,correction=_is_correction(message),reflection_marker=_is_reflect(message))
        return {'ok':True,'memory_id':mid,'old_level':old,'new_level':target,'exact_repeat_count':dup}
    except Exception as exc: return {'ok':False,'error':type(exc).__name__}

def audit(profile:str)->dict[str,Any]:
    try:
        with _db() as c:
            rows=c.execute("SELECT id,role,content,level FROM desktop_memory WHERE profile_id=? ORDER BY id",(profile,)).fetchall()
    except Exception: rows=[]
    users=[r for r in rows if r['role']=='user']; exact={}
    corrections=reflect=0
    for r in users:
        key=' '.join(str(r['content']).lower().split()); exact[key]=exact.get(key,0)+1
        corrections+=int(_is_correction(r['content'])); reflect+=int(_is_reflect(r['content']))
    duplicates=sum(v-1 for v in exact.values() if v>1)
    levels={k:0 for k in ('trace','working','episodic','core')}
    for r in rows:
        if r['level'] in levels: levels[r['level']]+=1
    return {'profile':profile,'memory_rows':len(rows),'user_turns':len(users),'exact_duplicate_turns':duplicates,'correction_turns':corrections,'reflection_markers':reflect,'levels':levels,'whole_history_retrieval':True,'correction_precedence':True}

def install(app):
    paths={getattr(r,'path','') for r in app.router.routes}
    if '/memory-quality/status' not in paths: app.include_router(router)

@router.get('/status')
def status(authorization:str|None=Header(default=None)):
    account=auth.require_account(authorization); return {'ok':True,**audit(str(account['username']))}
