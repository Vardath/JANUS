import importlib
import os


def fresh(tmp_path, monkeypatch):
    monkeypatch.setenv("JANUS_DB_PATH", str(tmp_path / "cost.sqlite3"))
    monkeypatch.setenv("JANUS_COST_PROFILE_DAILY_USD", "0.10")
    monkeypatch.setenv("JANUS_COST_PROFILE_MONTHLY_USD", "1.00")
    monkeypatch.setenv("JANUS_COST_BACKGROUND_DAILY_USD", "0.03")
    monkeypatch.setenv("JANUS_COST_GLOBAL_DAILY_USD", "10.0")
    import cost_governor
    return importlib.reload(cost_governor)


def test_profile_budget_and_accounting(tmp_path, monkeypatch):
    c=fresh(tmp_path,monkeypatch)
    assert c.authorize("alice","chat",0.04)["allowed"]
    c.record("alice","chat",estimated_usd=0.04,model="test")
    c.record("alice","foreground_core",estimated_usd=0.04,model="test")
    denied=c.authorize("alice","chat",0.03)
    assert not denied["allowed"]
    s=c.status("alice")
    assert round(s["today_estimated_usd"],2)==0.08
    assert s["denied_today"]==1
    assert c.status("bob")["today_estimated_usd"]==0


def test_optional_background_throttles_before_foreground(tmp_path, monkeypatch):
    c=fresh(tmp_path,monkeypatch)
    c.record("u","background_web",estimated_usd=0.025)
    assert not c.authorize("u","background_model",0.01)["allowed"]
    assert c.authorize("u","chat",0.01)["allowed"]


def test_scopes_are_nested_and_restored(tmp_path, monkeypatch):
    c=fresh(tmp_path,monkeypatch)
    assert c.current()==("__unattributed__","chat")
    with c.scope("alice","chat"):
        assert c.current()==("alice","chat")
        with c.scope("alice","vision"):
            assert c.current()==("alice","vision")
        assert c.current()==("alice","chat")
    assert c.current()==("__unattributed__","chat")
