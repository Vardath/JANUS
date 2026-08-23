"""Bounded direct URL / YouTube transcript ingestion for JANUS foreground research."""
from __future__ import annotations
import hashlib, html, json, os, re, sqlite3, time
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlparse, urlunparse
import requests

DB_PATH=os.environ.get('JANUS_DB_PATH','/data/janus.sqlite3')
MAX_URLS=max(1,int(os.environ.get('JANUS_URL_MAX_PER_TURN','3')))
MAX_CHARS=max(2000,int(os.environ.get('JANUS_URL_MAX_CHARS','12000')))
CACHE_SECONDS=max(300,int(os.environ.get('JANUS_URL_CACHE_SECONDS','86400')))
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
    if host.endswith('youtube.com'):
        if p.path=='/watch': return parse_qs(p.query).get('v',[''])[0]
        if p.path.startswith('/shorts/') or p.path.startswith('/live/'): return p.path.split('/')[2]
    return ''

def _youtube_channel(url):
    p=urlparse(url); host=p.netloc.lower().removeprefix('www.')
    if not host.endswith('youtube.com'): return False
    return p.path.startswith('/@') or p.path.startswith('/channel/') or p.path.startswith('/c/') or p.path.startswith('/user/')

def _canonical(url):
    p=urlparse(url.strip()); vid=_youtube_id(url)
    if vid: return 'https://youtube.com/watch?v='+vid
    return urlunparse((p.scheme.lower(),p.netloc.lower().removeprefix('www.'),p.path or '/','',p.query,''))

def _db():
    c=sqlite3.connect(DB_PATH,timeout=10); c.row_factory=sqlite3.Row
    c.execute("CREATE TABLE IF NOT EXISTS janus_url_cache(profile_id TEXT NOT NULL,canonical_url TEXT NOT NULL,kind TEXT NOT NULL,title TEXT NOT NULL DEFAULT '',content TEXT NOT NULL DEFAULT '',transcript_available INTEGER NOT NULL DEFAULT 0,provenance_json TEXT NOT NULL DEFAULT '{}',fetched_at REAL NOT NULL,PRIMARY KEY(profile_id,canonical_url))")
    c.commit(); return c

def _watch_caption_tracks(video_id):
    """Best-effort no-extra-dependency fallback for public caption tracks."""
    try:
        r=requests.get('https://www.youtube.com/watch',params={'v':video_id},timeout=10,headers={'User-Agent':'Mozilla/5.0 JANUSResearch/1.0'})
        if not r.ok: return []
        m=re.search(r'"captionTracks":(\[.*?\])\s*,\s*"audioTracks"',r.text,re.S)
        if not m: return []
        raw=m.group(1).replace('\\u0026','&')
        return json.loads(raw)
    except Exception:
        return []

def _caption_text_from_baseurl(base_url):
    try:
        r=requests.get(base_url,timeout=10,headers={'User-Agent':'JANUSResearch/1.0'})
        if not r.ok: return ''
        # XML timed-text and JSON-ish payloads are both reduced to readable text.
        bits=re.findall(r'<text[^>]*>(.*?)</text>',r.text,re.S|re.I)
        if bits:
            return ' '.join(html.unescape(re.sub(r'<[^>]+>',' ',b)) for b in bits)
        try:
            data=r.json(); events=data.get('events',[]) if isinstance(data,dict) else []
            segs=[]
            for e in events:
                for s in e.get('segs',[]) if isinstance(e,dict) else []:
                    if isinstance(s,dict) and s.get('utf8'): segs.append(str(s['utf8']))
            return ' '.join(segs)
        except Exception:
            return ''
    except Exception:
        return ''

def _fetch_youtube(url):
    vid=_youtube_id(url); title='YouTube video'; text=''; method='none'; note='transcript unavailable'
    # Preferred library path when deployment includes it.
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        api=YouTubeTranscriptApi(); rows=api.fetch(vid)
        text=' '.join(str(getattr(r,'text','')) for r in rows if getattr(r,'text',''))
        if text: method='youtube_transcript_api'
    except Exception as exc:
        note='transcript unavailable via API: '+type(exc).__name__
    # Built-in fallback avoids making transcript support depend entirely on one package/API shape.
    if not text:
        for track in _watch_caption_tracks(vid):
            base=str(track.get('baseUrl') or '') if isinstance(track,dict) else ''
            if not base: continue
            candidate=_caption_text_from_baseurl(base)
            if candidate.strip(): text=candidate; method='youtube_caption_track'; break
    try:
        r=requests.get('https://www.youtube.com/oembed',params={'url':'https://www.youtube.com/watch?v='+vid,'format':'json'},timeout=8,headers={'User-Agent':'JANUS/1.0'})
        if r.ok: title=str(r.json().get('title') or title)
    except Exception: pass
    available=bool(text.strip())
    if available: note=''
    return {'kind':'youtube','title':title,'content':' '.join(text.split())[:MAX_CHARS],'transcript_available':available,'note':note,'method':method}

def _fetch_web(url):
    r=requests.get(url,timeout=10,allow_redirects=True,headers={'User-Agent':'Mozilla/5.0 JANUSResearch/1.0','Accept':'text/html,text/plain,application/xhtml+xml,application/json'})
    r.raise_for_status(); ctype=(r.headers.get('content-type') or '').lower()
    if 'text/' not in ctype and 'html' not in ctype and 'json' not in ctype:
        return {'kind':'web','title':'URL','content':'','transcript_available':False,'note':'public URL is not readable text','method':'direct_http'}
    raw=r.text[:400000]
    if 'html' in ctype:
        parser=_Text(); parser.feed(raw); text=' '.join(parser.parts)
        m=re.search(r'<title[^>]*>(.*?)</title>',raw,re.I|re.S)
        title=html.unescape(re.sub('<[^>]+>',' ',m.group(1))).strip() if m else urlparse(url).netloc
    else: text=raw; title=urlparse(url).netloc
    return {'kind':'web','title':title[:300],'content':' '.join(html.unescape(text).split())[:MAX_CHARS],'transcript_available':False,'note':'','method':'direct_http'}

def ingest(profile,url):
    canonical=_canonical(url)
    with _db() as c:
        row=c.execute('SELECT * FROM janus_url_cache WHERE profile_id=? AND canonical_url=?',(profile,canonical)).fetchone()
        if row and time.time()-float(row['fetched_at'])<CACHE_SECONDS:
            d=dict(row); d['cached']=True; d['transcript_available']=bool(d['transcript_available']); d['provenance']=json.loads(d.pop('provenance_json') or '{}'); return d
    try:
        if _youtube_id(canonical): result=_fetch_youtube(canonical)
        elif _youtube_channel(canonical): result={'kind':'youtube_channel','title':'YouTube channel','content':'','transcript_available':False,'note':'channel URL detected; bounded web discovery required','method':'channel_discovery'}
        else: result=_fetch_web(canonical)
    except Exception as exc:
        result={'kind':'web','title':urlparse(canonical).netloc,'content':'','transcript_available':False,'note':'retrieval failed: '+type(exc).__name__,'method':'failed'}
    prov={'source_url':url,'canonical_url':canonical,'retrieved_at':_now(),'method':result.get('method','direct_http'),'content_sha256':hashlib.sha256(result.get('content','').encode()).hexdigest() if result.get('content') else ''}
    with _db() as c:
        c.execute('INSERT OR REPLACE INTO janus_url_cache(profile_id,canonical_url,kind,title,content,transcript_available,provenance_json,fetched_at) VALUES(?,?,?,?,?,?,?,?)',(profile,canonical,result['kind'],result['title'],result.get('content',''),1 if result.get('transcript_available') else 0,json.dumps(prov),time.time())); c.commit()
    result.update(canonical_url=canonical,provenance=prov,cached=False); return result

def capabilities(curiosity_module):
    return {'web_search':bool(getattr(curiosity_module,'ENABLED',False)),'direct_url_ingestion':True,'youtube_transcript_attempt':True,'youtube_caption_fallback':True,'youtube_channel_enumeration':'bounded via web search','transcript_policy':'per-video availability; never fabricated','url_cache':True,'account_isolated_cache':True,'max_urls_per_turn':MAX_URLS}

def install(app, curiosity_module):
    if getattr(curiosity_module,'_janus_url_ingest_installed',False): return
    original=curiosity_module.foreground_deliberate
    def wrapped(profile,message):
        urls=[]
        for u in URL_RE.findall(str(message or '')):
            u=u.rstrip('.,;:!?')
            if u not in urls: urls.append(u)
        notes=[]; channel_seen=False
        for u in urls[:MAX_URLS]:
            item=ingest(str(profile),u)
            if item.get('kind')=='youtube_channel': channel_seen=True
            status='transcript available' if item.get('transcript_available') else (item.get('note') or 'retrieved')
            notes.append('SOURCE URL: %s\nTITLE: %s\nSTATUS: %s\nPROVENANCE: %s\nRETRIEVED MATERIAL: %s' % (item.get('canonical_url',u),item.get('title',''),status,json.dumps(item.get('provenance',{}),ensure_ascii=False),item.get('content') or ''))
        enriched=str(message or '')
        if notes:
            enriched+='\n\nDIRECT URL MATERIAL (source evidence; never invent missing transcript text):\n'+'\n\n'.join(notes)
        if channel_seen:
            enriched+='\n\nWEB RESEARCH REQUIRED: this is a YouTube channel request. Use bounded web search to identify a small relevant/recent set of videos, then reason only from transcript/title/description evidence actually retrieved. Never claim full channel enumeration.'
        return original(profile,enriched)
    curiosity_module.foreground_deliberate=wrapped; curiosity_module._janus_url_ingest_installed=True
    app.state.janus_url_media_ingest=True
    @app.get('/capabilities/research')
    def research_capabilities(): return capabilities(curiosity_module)
