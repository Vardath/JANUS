"""Bounded direct URL / YouTube transcript ingestion for JANUS foreground research."""
from __future__ import annotations
import hashlib, html, json, os, re, sqlite3, time
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlparse, urlunparse
import requests
DB_PATH=os.environ.get('JANUS_DB_PATH','/data/janus.sqlite3'); MAX_URLS=3; MAX_CHARS=12000; CACHE_SECONDS=86400
URL_RE=re.compile(r'https?://[^\s<>\]\)\}]+',re.I)
class _Text(HTMLParser):
    def __init__(self): super().__init__(); self.parts=[]; self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in {'script','style','noscript','svg'}: self.skip+=1
    def handle_endtag(self,tag):
        if tag in {'script','style','noscript','svg'} and self.skip: self.skip-=1
    def handle_data(self,data):
        if not self.skip and data.strip(): self.parts.append(data.strip())
def _now(): return datetime.now(timezone.utc).isoformat()
def _youtube_id(url):
    p=urlparse(url); host=p.netloc.lower().removeprefix('www.')
    if host=='youtu.be': return p.path.strip('/').split('/')[0]
    if 'youtube.com' in host:
        if p.path=='/watch': return parse_qs(p.query).get('v',[''])[0]
        if p.path.startswith('/shorts/') or p.path.startswith('/live/'): return p.path.split('/')[2]
    return ''
def _canonical(url):
    p=urlparse(url.strip()); vid=_youtube_id(url)
    if vid: return 'https://youtube.com/watch?v='+vid
    return urlunparse((p.scheme.lower(),p.netloc.lower().removeprefix('www.'),p.path or '/','',p.query,''))
def _db():
    c=sqlite3.connect(DB_PATH,timeout=10); c.row_factory=sqlite3.Row
    c.execute("CREATE TABLE IF NOT EXISTS janus_url_cache(profile_id TEXT NOT NULL,canonical_url TEXT NOT NULL,kind TEXT NOT NULL,title TEXT NOT NULL DEFAULT '',content TEXT NOT NULL DEFAULT '',transcript_available INTEGER NOT NULL DEFAULT 0,provenance_json TEXT NOT NULL DEFAULT '{}',fetched_at REAL NOT NULL,PRIMARY KEY(profile_id,canonical_url))"); c.commit(); return c
def _fetch_youtube(url):
    vid=_youtube_id(url); title='YouTube video'; text=''; available=False; reason='transcript unavailable'
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        api=YouTubeTranscriptApi(); rows=api.fetch(vid); text=' '.join(str(getattr(r,'text','')) for r in rows if getattr(r,'text','')); available=bool(text); reason='' if available else reason
    except Exception as exc: reason='transcript unavailable: '+type(exc).__name__
    try:
        r=requests.get('https://www.youtube.com/oembed',params={'url':'https://www.youtube.com/watch?v='+vid,'format':'json'},timeout=8,headers={'User-Agent':'JANUS/1.0'})
        if r.ok: title=str(r.json().get('title') or title)
    except Exception: pass
    return {'kind':'youtube','title':title,'content':text[:MAX_CHARS],'transcript_available':available,'note':reason}
def _fetch_web(url):
    r=requests.get(url,timeout=10,allow_redirects=True,headers={'User-Agent':'Mozilla/5.0 JANUSResearch/1.0','Accept':'text/html,text/plain,application/xhtml+xml'}); r.raise_for_status(); ctype=(r.headers.get('content-type') or '').lower()
    if 'text/' not in ctype and 'html' not in ctype and 'json' not in ctype: return {'kind':'web','title':'URL','content':'','transcript_available':False,'note':'public URL is not readable text'}
    raw=r.text[:400000]
    if 'html' in ctype:
        parser=_Text(); parser.feed(raw); text=' '.join(parser.parts); m=re.search(r'<title[^>]*>(.*?)</title>',raw,re.I|re.S); title=html.unescape(re.sub('<[^>]+>',' ',m.group(1))).strip() if m else urlparse(url).netloc
    else: text=raw; title=urlparse(url).netloc
    return {'kind':'web','title':title[:300],'content':' '.join(html.unescape(text).split())[:MAX_CHARS],'transcript_available':False,'note':''}
def ingest(profile,url):
    canonical=_canonical(url)
    with _db() as c:
        row=c.execute('SELECT * FROM janus_url_cache WHERE profile_id=? AND canonical_url=?',(profile,canonical)).fetchone()
        if row and time.time()-float(row['fetched_at'])<CACHE_SECONDS:
            d=dict(row); d['cached']=True; d['transcript_available']=bool(d['transcript_available']); d['provenance']=json.loads(d.pop('provenance_json') or '{}'); return d
    try: result=_fetch_youtube(canonical) if _youtube_id(canonical) else _fetch_web(canonical)
    except Exception as exc: result={'kind':'web','title':urlparse(canonical).netloc,'content':'','transcript_available':False,'note':'retrieval failed: '+type(exc).__name__}
    prov={'source_url':url,'canonical_url':canonical,'retrieved_at':_now(),'method':'youtube_transcript' if result['kind']=='youtube' else 'direct_http','content_sha256':hashlib.sha256(result['content'].encode()).hexdigest() if result['content'] else ''}
    with _db() as c: c.execute('INSERT OR REPLACE INTO janus_url_cache(profile_id,canonical_url,kind,title,content,transcript_available,provenance_json,fetched_at) VALUES(?,?,?,?,?,?,?,?)',(profile,canonical,result['kind'],result['title'],result['content'],1 if result['transcript_available'] else 0,json.dumps(prov),time.time())); c.commit()
    result.update(canonical_url=canonical,provenance=prov,cached=False); return result
def install(app, curiosity_module):
    if getattr(curiosity_module,'_janus_url_ingest_installed',False): return
    original=curiosity_module.foreground_deliberate
    def wrapped(profile,message):
        urls=[]
        for u in URL_RE.findall(str(message or '')):
            u=u.rstrip('.,;:!?')
            if u not in urls: urls.append(u)
        notes=[]
        for u in urls[:MAX_URLS]:
            item=ingest(str(profile),u); status='transcript available' if item.get('transcript_available') else (item.get('note') or 'retrieved')
            notes.append('SOURCE URL: %s\nTITLE: %s\nSTATUS: %s\nPROVENANCE: %s\nRETRIEVED MATERIAL: %s' % (item.get('canonical_url',u),item.get('title',''),status,json.dumps(item.get('provenance',{}),ensure_ascii=False),item.get('content') or ''))
        enriched=str(message or '')
        if notes: enriched+='\n\nDIRECT URL MATERIAL (source evidence; never invent missing transcript text):\n'+'\n\n'.join(notes)
        return original(profile,enriched)
    curiosity_module.foreground_deliberate=wrapped; curiosity_module._janus_url_ingest_installed=True
    @app.get('/capabilities/research')
    def research_capabilities(): return {'web_search':bool(getattr(curiosity_module,'ENABLED',False)),'direct_url_ingestion':True,'youtube_transcript_attempt':True,'youtube_channel_enumeration':'bounded via web search','transcript_policy':'per-video availability; never fabricated','url_cache':True,'account_isolated_cache':True}
