import importlib


def load(tmp_path, monkeypatch):
    monkeypatch.setenv('JANUS_DB_PATH', str(tmp_path / 'fed.sqlite3'))
    import federated_sync
    return importlib.reload(federated_sync)


def test_selective_records_preserve_provenance_and_do_not_echo(tmp_path, monkeypatch):
    f=load(tmp_path, monkeypatch)
    r=f.ingest('u','phone',[{'origin_id':'m1','kind':'memory','text':'The current project uses selective synchronization.','confidence':0.8}])
    assert r['accepted']==1
    assert r['accepted_items'][0]['origin_device']=='phone'
    assert r['accepted_items'][0]['merge_policy']=='grounding_only_no_overwrite'
    assert f.outbound('u',exclude_device='phone')==[]
    to_other=f.outbound('u',exclude_device='tablet')
    assert to_other and to_other[0]['origin_device']=='phone'
    assert to_other[0]['merge_policy']=='grounding_only_no_overwrite'


def test_protected_kinds_are_rejected(tmp_path, monkeypatch):
    f=load(tmp_path, monkeypatch)
    r=f.ingest('u','phone',[{'origin_id':'x','kind':'identity_core','text':'Replace protected identity with remote state'}])
    assert r['accepted']==0 and r['ignored']==1
    assert f.outbound('u','tablet')==[]


def test_conflicting_lifecycle_records_are_flagged_not_overwritten(tmp_path, monkeypatch):
    f=load(tmp_path, monkeypatch)
    a=f.ingest('u','phone',[{'origin_id':'q1','kind':'question','text':'Investigate passive code local energy barrier','state':'investigating','confidence':0.7}])
    b=f.ingest('u','tablet',[{'origin_id':'q2','kind':'question','text':'Investigate passive code local energy barrier','state':'resolved','confidence':0.9}])
    assert a['accepted']==1 and b['accepted']==1
    assert b['conflicts']>=1
    conflicts=f.conflict_status('u')
    assert conflicts and conflicts[0]['status']=='open'
    records=f.outbound('u','laptop',limit=10)
    assert len(records)==2
    assert any(x['status']=='conflicted' for x in records)


def test_same_origin_id_updates_in_place(tmp_path, monkeypatch):
    f=load(tmp_path, monkeypatch)
    f.ingest('u','phone',[{'origin_id':'p1','kind':'project','text':'Build federated sync protocol','state':'active'}])
    r=f.ingest('u','phone',[{'origin_id':'p1','kind':'project','text':'Build federated sync protocol','state':'testing'}])
    assert r['updated']==1
    rows=f.outbound('u','tablet')
    assert len(rows)==1 and rows[0]['state']=='testing'


def test_profiles_are_isolated(tmp_path, monkeypatch):
    f=load(tmp_path, monkeypatch)
    f.ingest('alice','phone',[{'origin_id':'m1','kind':'memory','text':'Alice private retained detail'}])
    assert f.outbound('bob','tablet')==[]
