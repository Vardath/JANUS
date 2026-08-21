import importlib
import os
import tempfile


def test_cycle_metrics_detect_integration_imbalance(monkeypatch):
    fd,path=tempfile.mkstemp(suffix='.sqlite3'); os.close(fd)
    monkeypatch.setenv('JANUS_DB_PATH',path)
    import self_assessment as sa
    sa=importlib.reload(sa)
    cores={
        'evidence':{'cycle_count':7,'last_output':'evidence checked source'},
        'logic':{'cycle_count':7,'last_output':'logic checked implication'},
        'memory':{'cycle_count':6,'last_output':'memory retained question'},
        'novelty':{'cycle_count':5,'last_output':'novelty proposed test'},
        'counterpoint':{'cycle_count':27,'last_output':'feedback-only global feedback summary'},
        'consensus':{'cycle_count':27,'last_output':'consensus summary of prior consensus'},
        'interface':{'cycle_count':27,'last_output':'interface summary feedback-only'},
    }
    m=sa._cycle_metrics(cores)
    assert m['imbalance'] > 1.65
    assert m['self_reference'] > 0


def test_search_bridge_respects_caps(monkeypatch):
    fd,path=tempfile.mkstemp(suffix='.sqlite3'); os.close(fd)
    monkeypatch.setenv('JANUS_DB_PATH',path)
    monkeypatch.setenv('OPENAI_API_KEY','test-key')
    import curiosity_search as cs
    import epistemic_search_bridge as bridge
    cs=importlib.reload(cs); bridge=importlib.reload(bridge)
    monkeypatch.setattr(cs,'DAILY_CAP',1)
    monkeypatch.setattr(cs,'RELEVANT_CAP',1)
    with cs._db() as c:
        c.execute("INSERT INTO janus_curiosity_searches(profile_id,mode,query,rationale,status,created_at) VALUES(?,?,?,?,?,?)",('p','relevant','q','r','complete',cs._now()))
    assert bridge._request_relevant('p','test') is None
