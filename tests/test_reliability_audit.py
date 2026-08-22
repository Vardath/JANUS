import importlib
import sqlite3


def load(tmp_path, monkeypatch):
    db = tmp_path / "janus.sqlite3"
    monkeypatch.setenv("JANUS_DB_PATH", str(db))
    monkeypatch.setenv("JANUS_AUTH_DB", str(db))
    import auth, continuity_ledger, cost_governor, research_workspace, reliability_audit
    auth = importlib.reload(auth)
    continuity_ledger = importlib.reload(continuity_ledger)
    cost_governor = importlib.reload(cost_governor)
    research_workspace = importlib.reload(research_workspace)
    reliability_audit = importlib.reload(reliability_audit)
    with sqlite3.connect(db) as c:
        c.execute("CREATE TABLE IF NOT EXISTS desktop_memory(id INTEGER PRIMARY KEY AUTOINCREMENT,profile_id TEXT,role TEXT,content TEXT,level TEXT,created_at TEXT)")
    return db, continuity_ledger, cost_governor, research_workspace, reliability_audit


def test_audit_is_non_destructive_and_persists_history(tmp_path, monkeypatch):
    db, ledger, cost, research, audit = load(tmp_path, monkeypatch)
    ledger.create_item("alice", "question", "What remains?", state="investigating")
    cost.record("alice", "chat", estimated_usd=0.01)
    research.add_claim("alice", "Bounded claim", "A test claim.", "hypothesis", "untested")
    first = audit.run("alice")
    assert first["non_destructive"] is True
    assert first["autonomous_repair"] is False
    assert first["error_count"] == 0
    assert len(audit.history("alice")) == 1
    with sqlite3.connect(db) as c:
        assert c.execute("SELECT COUNT(*) FROM janus_continuity_items WHERE profile_id='alice'").fetchone()[0] == 1
        assert c.execute("SELECT COUNT(*) FROM janus_research_claims WHERE profile_id='alice'").fetchone()[0] == 1


def test_restart_preserves_continuity_and_audit_schema(tmp_path, monkeypatch):
    db, ledger, cost, research, audit = load(tmp_path, monkeypatch)
    item = ledger.create_item("alice", "project", "Restart persistence", state="active")
    audit.run("alice")
    ledger = importlib.reload(ledger)
    audit = importlib.reload(audit)
    assert ledger.get_item("alice", item["id"])["title"] == "Restart persistence"
    assert audit.history("alice")[0]["profile_id"] == "alice"
    with sqlite3.connect(db) as c:
        assert c.execute("SELECT value FROM janus_schema_meta WHERE key='reliability_schema_version'").fetchone()[0] == str(audit.SCHEMA_VERSION)


def test_profile_histories_are_isolated(tmp_path, monkeypatch):
    db, ledger, cost, research, audit = load(tmp_path, monkeypatch)
    audit.run("alice")
    audit.run("bob")
    assert len(audit.history("alice")) == 1
    assert len(audit.history("bob")) == 1
    assert audit.history("alice")[0]["profile_id"] == "alice"
    assert audit.history("bob")[0]["profile_id"] == "bob"


def test_audit_detects_duplicate_open_work_without_repairing_it(tmp_path, monkeypatch):
    db, ledger, cost, research, audit = load(tmp_path, monkeypatch)
    ledger.create_item("alice", "task", "Same task", state="active")
    ledger.create_item("alice", "task", "Same task", state="testing")
    out = audit.run("alice", persist=False)
    check = next(x for x in out["checks"] if x["name"] == "continuity_duplicate_pressure")
    assert check["ok"] is False
    assert check["severity"] == "warning"
    with sqlite3.connect(db) as c:
        assert c.execute("SELECT COUNT(*) FROM janus_continuity_items WHERE profile_id='alice'").fetchone()[0] == 2
