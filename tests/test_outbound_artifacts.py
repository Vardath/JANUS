import importlib
import sqlite3
from pathlib import Path


def load(tmp_path, monkeypatch):
    db = tmp_path / "janus.sqlite3"
    files = tmp_path / "files"
    monkeypatch.setenv("JANUS_DB_PATH", str(db))
    monkeypatch.setenv("JANUS_AUTH_DB", str(db))
    monkeypatch.setenv("JANUS_FILE_DIR", str(files))
    import auth, document_grounding, attachment_api, continuity_ledger, outbound_artifacts
    auth = importlib.reload(auth)
    document_grounding = importlib.reload(document_grounding)
    attachment_api = importlib.reload(attachment_api)
    continuity_ledger = importlib.reload(continuity_ledger)
    outbound_artifacts = importlib.reload(outbound_artifacts)
    return db, files, auth, attachment_api, continuity_ledger, outbound_artifacts


def add_account(db: Path, username: str, email: str) -> dict:
    with sqlite3.connect(db) as c:
        cur = c.execute(
            "INSERT INTO accounts(username,email,password_hash,created_at,updated_at,email_verified) VALUES(?,?,?,1,1,1)",
            (username, email, "test"),
        )
        aid = int(cur.lastrowid)
    return {"id": aid, "username": username, "email": email}


def test_continuity_report_is_account_bound_and_indexed(tmp_path, monkeypatch):
    db, files, auth, attachment_api, ledger, artifacts = load(tmp_path, monkeypatch)
    alice = add_account(db, "alice", "alice@example.test")
    ledger.create_item("alice", "question", "What remains to test?", "Preserve uncertainty.", state="investigating")
    req = artifacts.ArtifactRequest(kind="continuity_report", title="Alice continuity")
    out = artifacts.create_artifact(alice, req)
    assert out["file"]["filename"].endswith(".md")
    assert out["file"]["has_extracted_text"] is True
    assert out["file"]["document_index"]["chunks"] >= 1
    with sqlite3.connect(db) as c:
        row = c.execute("SELECT account_id,extracted_text FROM janus_files WHERE id=?", (out["file"]["id"],)).fetchone()
    assert row[0] == alice["id"]
    assert "What remains to test?" in row[1]


def test_project_snapshot_preserves_lifecycle_history(tmp_path, monkeypatch):
    db, files, auth, attachment_api, ledger, artifacts = load(tmp_path, monkeypatch)
    alice = add_account(db, "alice", "alice@example.test")
    item = ledger.create_item("alice", "project", "Selective sync", state="active")
    ledger.transition("alice", item["id"], "testing", "Regression run started")
    out = artifacts.create_artifact(alice, artifacts.ArtifactRequest(kind="project_snapshot", continuity_item_id=item["id"]))
    with sqlite3.connect(db) as c:
        text = c.execute("SELECT extracted_text FROM janus_files WHERE id=?", (out["file"]["id"],)).fetchone()[0]
    assert "Selective sync" in text
    assert "active → testing" in text
    assert out["provenance"]["continuity_item_id"] == item["id"]


def test_research_digest_exports_completed_research_and_sources(tmp_path, monkeypatch):
    db, files, auth, attachment_api, ledger, artifacts = load(tmp_path, monkeypatch)
    alice = add_account(db, "alice", "alice@example.test")
    with sqlite3.connect(db) as c:
        c.execute("""CREATE TABLE janus_curiosity_searches(
            id INTEGER PRIMARY KEY, profile_id TEXT, core_name TEXT, mode TEXT, query TEXT,
            result TEXT, sources_json TEXT, status TEXT, completed_at TEXT)""")
        c.execute(
            "INSERT INTO janus_curiosity_searches(id,profile_id,core_name,mode,query,result,sources_json,status,completed_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (1, "alice", "evidence", "relevant", "test query", "A concrete retrieved result", '[{"title":"Example","url":"https://example.test"}]', "complete", "2026-08-22T00:00:00Z"),
        )
    out = artifacts.create_artifact(alice, artifacts.ArtifactRequest(kind="research_digest", research_limit=5))
    with sqlite3.connect(db) as c:
        text = c.execute("SELECT extracted_text FROM janus_files WHERE id=?", (out["file"]["id"],)).fetchone()[0]
    assert "A concrete retrieved result" in text
    assert "https://example.test" in text
    assert out["provenance"]["research_ids"] == [1]


def test_artifacts_do_not_cross_accounts(tmp_path, monkeypatch):
    db, files, auth, attachment_api, ledger, artifacts = load(tmp_path, monkeypatch)
    alice = add_account(db, "alice", "alice@example.test")
    bob = add_account(db, "bob", "bob@example.test")
    out = artifacts.create_artifact(alice, artifacts.ArtifactRequest(kind="working_note", note="Alice private working note"))
    with sqlite3.connect(db) as c:
        assert c.execute("SELECT COUNT(*) FROM janus_outbound_artifacts WHERE account_id=?", (alice["id"],)).fetchone()[0] == 1
        assert c.execute("SELECT COUNT(*) FROM janus_outbound_artifacts WHERE account_id=?", (bob["id"],)).fetchone()[0] == 0
        assert c.execute("SELECT COUNT(*) FROM janus_files WHERE id=? AND account_id=?", (out["file"]["id"], bob["id"])).fetchone()[0] == 0
