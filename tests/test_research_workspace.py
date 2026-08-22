import importlib
import sqlite3


def load(tmp_path, monkeypatch):
    db = tmp_path / "janus.sqlite3"
    monkeypatch.setenv("JANUS_DB_PATH", str(db))
    monkeypatch.setenv("JANUS_AUTH_DB", str(db))
    import continuity_ledger, research_workspace
    continuity_ledger = importlib.reload(continuity_ledger)
    research_workspace = importlib.reload(research_workspace)
    return db, continuity_ledger, research_workspace


def test_seed_preserves_epistemic_boundaries_and_is_idempotent(tmp_path, monkeypatch):
    db, ledger, r = load(tmp_path, monkeypatch)
    first = r.seed_janus_program("alice")
    second = r.seed_janus_program("alice")
    assert first["created"] >= 10
    assert second["created"] == 0
    claims = {c["title"]: c for c in r.list_claims("alice", limit=500)}
    assert claims["Closed JANUS mathematical core"]["epistemic_state"] == "audited"
    assert claims["Passive symmetric energy barrier result"]["claim_kind"] == "negative_result"
    assert claims["Passive symmetric energy barrier result"]["epistemic_state"] == "closed_negative"
    assert claims["Distinctive observable"]["epistemic_state"] == "open"
    assert claims["Cosmological interpretation boundary"]["claim_kind"] == "boundary"
    context = r.workspace_context("alice")
    assert "Do not present hypotheses/interpretations as established physics" in context
    assert "closed_negative" in context


def test_open_research_questions_are_linked_to_continuity(tmp_path, monkeypatch):
    db, ledger, r = load(tmp_path, monkeypatch)
    r.seed_janus_program("alice")
    claims = r.list_claims("alice", limit=500)
    open_claim = next(c for c in claims if c["title"] == "Distinctive observable")
    assert open_claim["continuity_item_id"] is not None
    item = ledger.get_item("alice", int(open_claim["continuity_item_id"]))
    assert item["kind"] == "question"
    assert item["state"] == "investigating"


def test_evidence_does_not_automatically_upgrade_hypothesis(tmp_path, monkeypatch):
    db, ledger, r = load(tmp_path, monkeypatch)
    claim = r.add_claim("alice", "Candidate bridge", "A speculative physical bridge.", "hypothesis", "untested", domain="physical-bridge")
    r.add_evidence("alice", claim["id"], "calculation", "One algebraic consistency check passed.", result="consistent")
    refreshed = r.get_claim("alice", claim["id"])
    assert refreshed["epistemic_state"] == "untested"
    assert len(refreshed["evidence"]) == 1


def test_negative_result_remains_available_and_profile_isolated(tmp_path, monkeypatch):
    db, ledger, r = load(tmp_path, monkeypatch)
    neg = r.add_claim("alice", "Failed candidate", "Candidate failed a falsification test.", "negative_result", "closed_negative", domain="test")
    assert r.get_claim("alice", neg["id"])["epistemic_state"] == "closed_negative"
    try:
        r.get_claim("bob", neg["id"])
        assert False
    except KeyError:
        pass
    assert r.list_claims("bob") == []


def test_state_change_is_explicit_and_audited_as_critique(tmp_path, monkeypatch):
    db, ledger, r = load(tmp_path, monkeypatch)
    claim = r.add_claim("alice", "Prediction candidate", "Would imply measurable X.", "prediction", "provisional")
    changed = r.update_epistemic_state("alice", claim["id"], "contradicted", "Existing observation rules out X.")
    assert changed["epistemic_state"] == "contradicted"
    assert any(e["evidence_kind"] == "critique" and "rules out X" in e["summary"] for e in changed["evidence"])
