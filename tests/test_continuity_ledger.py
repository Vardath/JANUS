import importlib


def load(tmp_path, monkeypatch):
    monkeypatch.setenv('JANUS_DB_PATH', str(tmp_path / 'ledger.sqlite3'))
    import continuity_ledger
    return importlib.reload(continuity_ledger)


def test_question_lifecycle_and_context(tmp_path, monkeypatch):
    c=load(tmp_path, monkeypatch)
    q=c.create_item('u','question','Does the passive code have a local energy barrier?',state='investigating',priority=80,tags=['qec'])
    assert q['state']=='investigating'
    assert 'passive code' in c.continuity_context('u')
    q=c.transition('u',q['id'],'provisional','Flat-gap construction is negative; other local families remain open.')
    assert q['state']=='provisional'
    q=c.transition('u',q['id'],'resolved','Search completed.')
    assert q['state']=='resolved'
    assert 'passive code' not in c.continuity_context('u')


def test_supersession_marks_old_item_not_current(tmp_path, monkeypatch):
    c=load(tmp_path, monkeypatch)
    old=c.create_item('u','task','Implement old sync design',state='active')
    new=c.create_item('u','task','Implement selective federated sync',state='approved',supersedes_id=old['id'])
    assert c.get_item('u',old['id'])['state']=='superseded'
    assert c.get_item('u',new['id'])['state']=='approved'
    open_titles={x['title'] for x in c.list_items('u',open_only=True)}
    assert new['title'] in open_titles and old['title'] not in open_titles


def test_profiles_are_isolated(tmp_path, monkeypatch):
    c=load(tmp_path, monkeypatch)
    item=c.create_item('alice','idea','Private idea',state='active')
    assert c.list_items('bob') == []
    try:
        c.get_item('bob',item['id'])
        assert False
    except KeyError:
        pass
