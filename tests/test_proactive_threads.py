import importlib


def load(tmp_path, monkeypatch):
    monkeypatch.setenv('JANUS_DB_PATH', str(tmp_path / 'threads.sqlite3'))
    import continuity_ledger
    import proactive_threads
    continuity_ledger = importlib.reload(continuity_ledger)
    proactive_threads = importlib.reload(proactive_threads)
    return continuity_ledger, proactive_threads


def test_links_message_to_matching_open_question(tmp_path, monkeypatch):
    ledger, threads = load(tmp_path, monkeypatch)
    q = ledger.create_item('u','question','Does passive error correction have a local energy barrier?',
                           'Investigate local Hamiltonian families and minimum-energy logical paths.',
                           state='investigating', priority=90)
    r = threads.resolve_thread('u','A new local Hamiltonian calculation suggests the energy barrier may remain flat for this passive error correction construction.')
    assert r['continuity_item_id'] == q['id']
    assert r['thread_key'] == f"continuity:{q['id']}"
    bound = threads.bind_message(17,'u','curiosity_search_complete',4,'energy barrier result',r)
    assert threads.get_thread('u',17)['continuity']['state'] == 'investigating'
    assert bound['title'] == q['title']


def test_unrelated_material_stays_background_not_false_project_link(tmp_path, monkeypatch):
    ledger, threads = load(tmp_path, monkeypatch)
    ledger.create_item('u','project','Selective federated memory synchronization','Provenance and no overwrite.',state='active')
    r = threads.resolve_thread('u','A paper about coral fluorescence under moonlight reported an unusual spectral response.')
    assert r['continuity_item_id'] is None
    assert r['thread_type'] == 'background'


def test_followup_uses_latest_thread_without_mutating_lifecycle(tmp_path, monkeypatch):
    ledger, threads = load(tmp_path, monkeypatch)
    q = ledger.create_item('u','question','Could two distinct research findings imply a testable prediction?',state='investigating')
    r = {'thread_key':f"continuity:{q['id']}",'thread_type':'question','title':q['title'],'continuity_item_id':q['id'],'confidence':0.9,'state':'investigating'}
    threads.bind_message(21,'u','background_synthesis',9,'testable prediction',r)
    context, thread = threads.format_chat_context('u','Tell me more about that')
    assert thread['event_id'] == 21
    assert 'Continue this subject naturally' in context
    assert ledger.get_item('u',q['id'])['state'] == 'investigating'


def test_explicit_reply_and_profile_isolation(tmp_path, monkeypatch):
    ledger, threads = load(tmp_path, monkeypatch)
    threads.bind_message(30,'alice','background_reflection',None,'novel telescope calibration result')
    assert threads.get_thread('bob',30) is None
    context, linked = threads.format_chat_context('alice','Why does this matter?',30)
    assert linked and linked['event_id'] == 30
    assert context
    context2, linked2 = threads.format_chat_context('bob','Tell me more about that',30)
    assert linked2 is None and context2 == ''
