import importlib
import sqlite3

import pytest
from fastapi import HTTPException


def load(tmp_path, monkeypatch):
    db = tmp_path / "janus.sqlite3"
    monkeypatch.setenv("JANUS_DB_PATH", str(db))
    monkeypatch.setenv("JANUS_VISUAL_REVENUE_GATE", "0")
    monkeypatch.setenv("JANUS_VISUAL_DELIBERATION_RENDERING", "0")
    import visual_deliberation as vd
    vd = importlib.reload(vd)
    with sqlite3.connect(db) as c:
        c.execute("CREATE TABLE IF NOT EXISTS accounts(id INTEGER PRIMARY KEY, username TEXT, disabled INTEGER DEFAULT 0)")
        c.execute("INSERT INTO accounts(id,username,disabled) VALUES(1,'alice',0)")
        c.execute("INSERT INTO accounts(id,username,disabled) VALUES(2,'bob',0)")
    return db, vd, {"id": 1, "username": "alice"}, {"id": 2, "username": "bob"}


def test_step9_scaffold_never_enables_renderer(tmp_path, monkeypatch):
    db, vd, alice, bob = load(tmp_path, monkeypatch)
    status = vd.policy_status()
    assert status["scaffolding_enabled"] is True
    assert status["autonomous_rendering_enabled"] is False
    assert status["background_rendering_enabled"] is False
    run = vd.start(alice, vd.StartRequest(topic="Explain a Fano-plane mapping visually"))
    assert run["rendering_enabled"] is False
    assert run["state"] == "open"


def test_concept_critique_selection_pipeline_is_externalizable(tmp_path, monkeypatch):
    db, vd, alice, bob = load(tmp_path, monkeypatch)
    run = vd.start(alice, vd.StartRequest(topic="Show selective sync flow"))
    did = run["id"]
    run = vd.add_record(alice, did, vd.RecordRequest(core="novelty", kind="concept", candidate_id="c1", text="Use a local-global bridge diagram."))
    assert run["counts"]["concepts"] == 1
    run = vd.add_record(alice, did, vd.RecordRequest(core="counterpoint", kind="critique", candidate_id="c1", text="Make conflict provenance visible."))
    assert run["counts"]["critiques"] == 1
    run = vd.add_record(alice, did, vd.RecordRequest(core="consensus", kind="selection", candidate_id="c1", text="Select the bridge diagram with provenance labels."))
    assert run["counts"]["selections"] == 1
    assert run["state"] == "selected"
    assert [r["kind"] for r in run["records"]] == ["concept", "critique", "selection"]


def test_only_consensus_or_interface_can_select(tmp_path, monkeypatch):
    db, vd, alice, bob = load(tmp_path, monkeypatch)
    did = vd.start(alice, vd.StartRequest(topic="Visual hierarchy"))["id"]
    with pytest.raises(HTTPException) as exc:
        vd.add_record(alice, did, vd.RecordRequest(core="logic", kind="selection", text="Pick concept A"))
    assert exc.value.status_code == 400


def test_revision_and_concept_limits_are_hard(tmp_path, monkeypatch):
    db, vd, alice, bob = load(tmp_path, monkeypatch)
    did = vd.start(alice, vd.StartRequest(topic="Bounded visual experiment"))["id"]
    with pytest.raises(HTTPException) as exc:
        vd.add_record(alice, did, vd.RecordRequest(core="novelty", kind="concept", text="Too many revisions", revision=vd.MAX_REVISIONS + 1))
    assert exc.value.status_code == 429
    for i in range(vd.MAX_CONCEPTS):
        vd.add_record(alice, did, vd.RecordRequest(core="novelty", kind="concept", candidate_id=f"c{i}", text=f"Concept {i}"))
    with pytest.raises(HTTPException) as exc:
        vd.add_record(alice, did, vd.RecordRequest(core="novelty", kind="concept", candidate_id="overflow", text="Overflow concept"))
    assert exc.value.status_code == 429


def test_visual_deliberations_are_account_isolated(tmp_path, monkeypatch):
    db, vd, alice, bob = load(tmp_path, monkeypatch)
    did = vd.start(alice, vd.StartRequest(topic="Alice private visual plan"))["id"]
    assert vd.list_runs(alice)["items"][0]["id"] == did
    assert vd.list_runs(bob)["items"] == []
    with pytest.raises(HTTPException) as exc:
        vd.get(bob, did)
    assert exc.value.status_code == 404
