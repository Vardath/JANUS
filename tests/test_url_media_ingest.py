import importlib, os

def fresh(tmp_path,monkeypatch):
    monkeypatch.setenv('JANUS_DB_PATH',str(tmp_path/'url.sqlite3'))
    import url_media_ingest as m
    return importlib.reload(m)

def test_youtube_ids_and_channel_detection(tmp_path,monkeypatch):
    m=fresh(tmp_path,monkeypatch)
    assert m._youtube_id('https://youtu.be/abc123')=='abc123'
    assert m._youtube_id('https://www.youtube.com/watch?v=abc123')=='abc123'
    assert m._youtube_channel('https://www.youtube.com/@Example') is True

def test_cache_is_profile_isolated(tmp_path,monkeypatch):
    m=fresh(tmp_path,monkeypatch)
    monkeypatch.setattr(m,'_fetch_web',lambda url:{'kind':'web','title':'T','content':'hello','transcript_available':False,'note':'','method':'test'})
    a=m.ingest('alice','https://example.com/a')
    b=m.ingest('alice','https://example.com/a')
    c=m.ingest('bob','https://example.com/a')
    assert a['cached'] is False and b['cached'] is True and c['cached'] is False

def test_missing_transcript_is_not_fabricated(tmp_path,monkeypatch):
    m=fresh(tmp_path,monkeypatch)
    monkeypatch.setattr(m,'_watch_caption_tracks',lambda vid:[])
    class R:
        ok=False
    monkeypatch.setattr(m.requests,'get',lambda *a,**k:R())
    item=m._fetch_youtube('https://youtube.com/watch?v=abc123')
    assert item['transcript_available'] is False
    assert item['content']==''
    assert 'unavailable' in item['note']

def test_capability_report_is_specific(tmp_path,monkeypatch):
    m=fresh(tmp_path,monkeypatch)
    class C: ENABLED=True
    c=m.capabilities(C)
    assert c['direct_url_ingestion'] is True
    assert c['youtube_transcript_attempt'] is True
    assert 'never fabricated' in c['transcript_policy']
