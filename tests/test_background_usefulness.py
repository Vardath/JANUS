import importlib
import sqlite3


def _module(tmp_path, monkeypatch):
    path=tmp_path/'janus.sqlite3'
    monkeypatch.setenv('JANUS_DB_PATH', str(path))
    import background_usefulness as bu
    return importlib.reload(bu), path


def test_concrete_novel_research_passes(tmp_path, monkeypatch):
    bu,_=_module(tmp_path, monkeypatch)
    out=bu.assess_text(
        'Compare recent measurements of volcanic lightning charge separation with laboratory ash-plume experiments; what mechanism would distinguish the models?',
        ['distributed memory quorum recovery under node failures'],
    )
    assert out['pass'] is True
    assert out['novelty'] > 0.6
    assert out['process_ratio'] < bu.PROCESS_RATIO_BLOCK


def test_recursive_process_topic_is_suppressed(tmp_path, monkeypatch):
    bu,_=_module(tmp_path, monkeypatch)
    out=bu.assess_text('What are the cores thinking about the JANUS cycle, consensus and interface processing right now?')
    assert out['pass'] is False
    assert 'self-referential-loop' in out['reasons'] or 'process-heavy' in out['reasons']


def test_near_duplicate_research_is_suppressed(tmp_path, monkeypatch):
    bu,_=_module(tmp_path, monkeypatch)
    old='Find current evidence about distributed memory fault recovery and quorum behaviour under node failures'
    new='Find current evidence about distributed memory fault recovery and quorum behaviour when nodes fail'
    out=bu.assess_text(new,[old])
    assert out['pass'] is False
    assert out['max_similarity'] >= bu.REPETITION_BLOCK


def test_gate_records_suppression_without_search_spend(tmp_path, monkeypatch):
    bu,path=_module(tmp_path, monkeypatch)
    with sqlite3.connect(path) as c:
        c.execute('''CREATE TABLE janus_curiosity_searches(
            id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id TEXT, core_name TEXT, mode TEXT,
            query TEXT, rationale TEXT, result TEXT, sources_json TEXT, status TEXT, created_at TEXT, completed_at TEXT)''')
        c.execute("INSERT INTO janus_curiosity_searches(profile_id,core_name,mode,query,rationale,result,sources_json,status,created_at) VALUES('p','evidence','relevant','distributed memory quorum recovery','', '', '[]','complete','2026-08-22T00:00:00Z')")
    out=bu.gate_candidate('p','logic','relevant','distributed memory quorum recovery','repeat the same background topic')
    assert out['pass'] is False
    with sqlite3.connect(path) as c:
        row=c.execute("SELECT decision,event_kind FROM janus_background_usefulness WHERE profile_id='p'").fetchone()
    assert row == ('suppress','candidate')


def test_rationale_cannot_dilute_exact_duplicate(tmp_path, monkeypatch):
    bu,path=_module(tmp_path, monkeypatch)
    with sqlite3.connect(path) as c:
        c.execute('''CREATE TABLE janus_curiosity_searches(
            id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id TEXT, core_name TEXT, mode TEXT,
            query TEXT, rationale TEXT, result TEXT, sources_json TEXT, status TEXT, created_at TEXT, completed_at TEXT)''')
        c.execute("INSERT INTO janus_curiosity_searches(profile_id,core_name,mode,query,rationale,result,sources_json,status,created_at) VALUES('p','evidence','relevant','distributed memory quorum recovery','', '', '[]','complete','2026-08-22T00:00:00Z')")
    out=bu.gate_candidate(
        'p','logic','relevant','distributed memory quorum recovery',
        'A much longer rationale about engineering tradeoffs, failure domains, source quality, and alternate mechanisms that must not make the duplicated query look novel.'
    )
    assert out['pass'] is False
    assert out['max_similarity'] >= bu.REPETITION_BLOCK
    assert 'near-duplicate' in out['reasons']


def test_morphology_normalization_catches_failure_variants(tmp_path, monkeypatch):
    bu,_=_module(tmp_path, monkeypatch)
    old='Find current evidence about distributed memory fault recovery and quorum behaviour under node failures'
    variants=[
        'Find current evidence about distributed memory fault recovery and quorum behaviour when nodes fail',
        'Find current evidence about distributed memory fault recovery and quorum behaviour under node failure',
    ]
    for new in variants:
        out=bu.assess_text(new,[old])
        assert out['pass'] is False
        assert out['max_similarity'] >= bu.REPETITION_BLOCK


def test_audit_reports_useful_and_repetitive_outputs(tmp_path, monkeypatch):
    bu,path=_module(tmp_path, monkeypatch)
    with sqlite3.connect(path) as c:
        c.execute('''CREATE TABLE janus_curiosity_searches(
            id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id TEXT, core_name TEXT, mode TEXT,
            query TEXT, rationale TEXT, result TEXT, sources_json TEXT, status TEXT, created_at TEXT, completed_at TEXT)''')
        rows=[
            ('p','evidence','relevant','volcanic lightning','',
             'A field study measured charge separation in volcanic ash plumes and compared observations with laboratory experiments; the data support a collision-driven charging mechanism.',
             '[{"title":"study","url":"https://example.test/a"}]','complete','2026-08-22T00:00:00Z','2026-08-22T00:01:00Z'),
            ('p','logic','adjacent','volcanic lightning repeat','',
             'A field study measured charge separation in volcanic ash plumes and compared observations with laboratory experiments; the data support a collision-driven charging mechanism.',
             '[]','complete','2026-08-22T01:00:00Z','2026-08-22T01:01:00Z'),
        ]
        c.executemany('INSERT INTO janus_curiosity_searches(profile_id,core_name,mode,query,rationale,result,sources_json,status,created_at,completed_at) VALUES(?,?,?,?,?,?,?,?,?,?)',rows)
    report=bu.audit('p')
    assert report['completed_scored'] == 2
    assert report['useful'] >= 1
    assert report['repetitive'] >= 1


def test_install_wraps_only_background_choice(tmp_path, monkeypatch):
    bu,_=_module(tmp_path, monkeypatch)
    class Dummy:
        _janus_background_usefulness_installed=False
        @staticmethod
        def _choose_search(profile):
            return ('evidence','relevant','What are the cores thinking about the JANUS cycle and consensus interface processing?','self status')
    bu.install(Dummy)
    assert Dummy._choose_search('p') is None
    assert Dummy._janus_background_usefulness_installed is True
