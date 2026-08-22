import importlib


def load(tmp_path,monkeypatch):
    monkeypatch.setenv('JANUS_DB_PATH',str(tmp_path/'continuity.sqlite3'))
    import continuity_ledger, continuity_governance
    importlib.reload(continuity_ledger)
    return importlib.reload(continuity_governance), continuity_ledger


def test_explicit_completion_updates_matching_item(tmp_path,monkeypatch):
    g,l=load(tmp_path,monkeypatch)
    item=l.create_item('u','task','Implement selective federated memory sync','Conflict-aware local/global exchange',state='active')
    result=g.apply_explicit_update('u','We finished selective federated memory sync.')
    assert result['applied'] is True
    assert l.get_item('u',item['id'])['state']=='completed'


def test_ambiguous_that_is_done_never_guesses(tmp_path,monkeypatch):
    g,l=load(tmp_path,monkeypatch)
    l.create_item('u','task','First task',state='active')
    l.create_item('u','task','Second task',state='active')
    result=g.apply_explicit_update('u','That is done.')
    assert result['recognized'] is True
    assert result['applied'] is False
    assert all(x['state']=='active' for x in l.list_items('u'))


def test_contradicted_history_is_retained_but_not_open(tmp_path,monkeypatch):
    g,l=load(tmp_path,monkeypatch)
    item=l.create_item('u','research','Passive Steane barrier hypothesis','Check for growing barrier',state='investigating')
    result=g.apply_explicit_update('u','The passive Steane barrier hypothesis was contradicted.')
    assert result['applied']
    assert l.get_item('u',item['id'])['state']=='contradicted'
    assert item['id'] not in {x['id'] for x in l.list_items('u',open_only=True)}
    assert 'contradicted' in g.currentness_context('u','Steane barrier')


def test_reopen_is_explicit_and_audited(tmp_path,monkeypatch):
    g,l=load(tmp_path,monkeypatch)
    item=l.create_item('u','question','Order four physical observable','Deferred test',state='deferred')
    result=g.apply_explicit_update('u','Reopen the order four physical observable question.')
    assert result['applied']
    assert l.get_item('u',item['id'])['state']=='reopened'
    ev=l.events('u',item['id'])
    assert any(e['new_state']=='reopened' for e in ev)
