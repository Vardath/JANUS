import importlib
import os
import tempfile


def _module(monkeypatch):
    fd,path=tempfile.mkstemp(suffix='.sqlite3'); os.close(fd)
    monkeypatch.setenv('JANUS_DB_PATH',path)
    import background_cognition as bc
    return importlib.reload(bc), path


def test_repeated_background_query_is_detected(monkeypatch):
    bc,_=_module(monkeypatch)
    recent=[
        'Find current reliable information about distributed memory fault recovery and quorum behaviour',
        'Learn about animal navigation using magnetic fields',
    ]
    q='Find reliable current information about distributed memory fault recovery and quorum behaviour'
    assert bc.query_is_repetitive(q,recent) is True


def test_distinct_background_query_is_not_suppressed(monkeypatch):
    bc,_=_module(monkeypatch)
    recent=['distributed memory fault recovery and quorum behaviour']
    q='recent observations of volcanic lightning and charge separation in ash plumes'
    assert bc.query_is_repetitive(q,recent) is False


def test_pair_selection_avoids_duplicate_research(monkeypatch):
    bc,path=_module(monkeypatch)
    with bc._db() as c:
        c.execute('''CREATE TABLE janus_curiosity_searches(
            id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id TEXT, core_name TEXT, mode TEXT,
            query TEXT, result TEXT, sources_json TEXT, status TEXT, completed_at TEXT)''')
        rows=[
            ('p','evidence','relevant','memory fault tolerance','Distributed memory systems use quorum rules to survive node failures and distinguish local faults from agreement failures.','[]','complete','2026-08-22T01:00:00+00:00'),
            ('p','logic','adjacent','error correcting codes','Error correcting codes use redundant constraints to identify and repair local errors; correlated errors can defeat simple independence assumptions.','[]','complete','2026-08-22T02:00:00+00:00'),
            ('p','context','adjacent','memory fault tolerance duplicate','Distributed memory systems use quorum rules to survive node failures and distinguish local faults from agreement failures.','[]','complete','2026-08-22T03:00:00+00:00'),
        ]
        c.executemany('INSERT INTO janus_curiosity_searches(profile_id,core_name,mode,query,result,sources_json,status,completed_at) VALUES(?,?,?,?,?,?,?,?)',rows)
    pair=bc._choose_pair('p')
    assert pair is not None
    a,b=pair
    assert bc.similarity(a['result'],b['result']) < 0.55
    assert int(a['id']) != int(b['id'])


def test_topic_signature_is_human_subject_matter(monkeypatch):
    bc,_=_module(monkeypatch)
    sig=bc.topic_signature('A recent study compared volcanic lightning, ash charge separation, and atmospheric electrical discharge.')
    assert 'volcanic' in sig or 'lightning' in sig
    assert 'janus' not in sig
