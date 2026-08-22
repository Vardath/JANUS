import importlib

def fresh(tmp_path,monkeypatch):
    monkeypatch.setenv('JANUS_DB_PATH',str(tmp_path/'owner.sqlite3'))
    import cost_governor, owner_observability
    importlib.reload(cost_governor)
    return importlib.reload(owner_observability),cost_governor

def test_owner_status_healthy(tmp_path,monkeypatch):
    o,c=fresh(tmp_path,monkeypatch)
    s=o.snapshot('owner',{'server_runtime_thread_alive':True,'remote_clients':1,'registered_clients':1,'presence_state':'connected','phase':'wake'})
    assert s['state']=='healthy'
    assert not s['needs_attention']
    assert s['local_devices']['online']==1
    assert s['policy']['background_work_degrades_before_foreground_chat'] is True

def test_owner_status_explains_degradation(tmp_path,monkeypatch):
    o,c=fresh(tmp_path,monkeypatch)
    c.record('owner','background_web',estimated_usd=0,status='timeout',detail='provider timed out')
    s=o.snapshot('owner',{'server_runtime_thread_alive':True,'remote_clients':0,'registered_clients':1,'presence_state':'registered-offline','phase':'sleep'})
    assert s['state']=='degraded'
    assert s['needs_attention']
    assert s['provider_failures'][0]['status']=='timeout'
    assert any('offline' in x.lower() for x in s['explanations'])
    assert any('provider' in x.lower() for x in s['explanations'])

def test_stopped_server_requests_attention(tmp_path,monkeypatch):
    o,c=fresh(tmp_path,monkeypatch)
    s=o.snapshot('owner',{'server_runtime_thread_alive':False,'remote_clients':0,'registered_clients':0,'phase':'unknown'})
    assert s['state']=='attention'
    assert s['server']['background_cycle_running'] is False
