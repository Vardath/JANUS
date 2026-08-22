import importlib, sqlite3


def load(tmp_path, monkeypatch):
    db=tmp_path/'janus.sqlite3'; monkeypatch.setenv('JANUS_DB_PATH',str(db))
    import memory_quality as mq
    mq=importlib.reload(mq)
    with sqlite3.connect(db) as c:
        c.execute('CREATE TABLE desktop_memory(id INTEGER PRIMARY KEY AUTOINCREMENT,profile_id TEXT NOT NULL,role TEXT NOT NULL,content TEXT NOT NULL,level TEXT NOT NULL DEFAULT "trace",created_at TEXT NOT NULL)')
    return mq,db


def add(db, profile, role, text, level='trace'):
    with sqlite3.connect(db) as c:
        c.execute('INSERT INTO desktop_memory(profile_id,role,content,level,created_at) VALUES(?,?,?,?,?)',(profile,role,text,level,'2026-08-22T00:00:00Z'))


def test_whole_history_retrieves_old_relevant_turn_beyond_recent_window(tmp_path,monkeypatch):
    mq,db=load(tmp_path,monkeypatch)
    add(db,'p','user','My enclosure cosmology has a flooded sky and four lands above it.','episodic')
    for i in range(40): add(db,'p','user',f'unrelated recent message number {i}')
    ctx=mq.format_context('p','What did I say about the flooded sky and four lands?')
    assert 'flooded sky' in ctx and 'four lands' in ctx


def test_correction_is_ranked_and_marked_over_conflicting_older_material(tmp_path,monkeypatch):
    mq,db=load(tmp_path,monkeypatch)
    add(db,'p','user','The project is my cosmology.','working')
    add(db,'p','user','Correction: that is not my cosmology; it is the mathematical JANUS research.','working')
    ctx=mq.format_context('p','Is the JANUS mathematics my cosmology?')
    assert 'CORRECTION/CLARIFICATION' in ctx
    assert 'not my cosmology' in ctx


def test_ponder_and_remember_promote_salient_user_turn(tmp_path,monkeypatch):
    mq,db=load(tmp_path,monkeypatch)
    text='Think about this and ponder it; remember this distinction for later.'
    add(db,'p','user',text,'trace')
    out=mq.reinforce_after_turn('p',text)
    assert out['new_level']=='working'
    with sqlite3.connect(db) as c:
        assert c.execute('SELECT level FROM desktop_memory WHERE profile_id="p"').fetchone()[0]=='working'


def test_exact_repetition_is_measured_not_duplicated_in_retrieval_context(tmp_path,monkeypatch):
    mq,db=load(tmp_path,monkeypatch)
    text='Remember the distinction between the mathematical JANUS project and the cosmology.'
    add(db,'p','user',text,'working'); add(db,'p','user',text,'working')
    ctx=mq.format_context('p','What distinction should you remember?')
    assert ctx.count(text)==1
    report=mq.audit('p')
    assert report['exact_duplicate_turns']==1


def test_account_history_isolated(tmp_path,monkeypatch):
    mq,db=load(tmp_path,monkeypatch)
    add(db,'alice','user','Alice private lunar research','episodic')
    add(db,'bob','user','Bob private ocean research','episodic')
    assert 'Alice private' not in mq.format_context('bob','lunar research')


def test_retrieval_does_not_promote_unrelated_low_value_turns(tmp_path,monkeypatch):
    mq,db=load(tmp_path,monkeypatch)
    add(db,'p','user','hello there','trace')
    mq.format_context('p','completely unrelated geometry question')
    with sqlite3.connect(db) as c:
        assert c.execute('SELECT level FROM desktop_memory').fetchone()[0]=='trace'
