import base64
import importlib
import os
import tempfile
import time
from pathlib import Path


def _fresh(tmp: Path):
    os.environ["JANUS_DB_PATH"] = str(tmp / "janus.sqlite3")
    os.environ["JANUS_AUTH_DB"] = str(tmp / "janus.sqlite3")
    os.environ["JANUS_FILE_DIR"] = str(tmp / "files")
    os.environ["JANUS_FILE_STALE_SECONDS"] = str(86400)
    os.environ["JANUS_FILE_STORAGE_SOFT_BYTES"] = str(64 * 1024 * 1024)
    os.environ["JANUS_FILE_STORAGE_HARD_BYTES"] = str(128 * 1024 * 1024)
    import auth
    import attachment_api
    import attachment_retention
    importlib.reload(auth)
    importlib.reload(attachment_api)
    importlib.reload(attachment_retention)
    return auth, attachment_api, attachment_retention


def _client(auth, attachment_api):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI()
    app.include_router(auth.router)
    app.include_router(attachment_api.router)
    return TestClient(app)


def _register(client, username, email):
    r = client.post("/auth/register", json={"username": username, "email": email, "password": "password12345"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _upload(client, token, name, content):
    r = client.post("/files/upload", headers={"Authorization": f"Bearer {token}"}, json={
        "filename": name,
        "mime_type": "text/plain",
        "data_base64": base64.b64encode(content).decode("ascii"),
    })
    assert r.status_code == 200, r.text
    return r.json()["file"]["id"]


def _age_files(retention, seconds=10 * 86400):
    old = int(time.time()) - seconds
    retention.init_retention_schema()
    with retention._db() as c:
        c.execute("UPDATE janus_files SET created_at=?,last_touched_at=?,last_referenced_at=0", (old, old))


def test_audit_keeps_useful_content_and_deletes_low_value_stale_file():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        auth, attachment_api, retention = _fresh(tmp)
        client = _client(auth, attachment_api)
        token = _register(client, "audituser", "audit@example.com")
        useful_id = _upload(client, token, "research.md", ("meaningful retained context " * 250).encode())
        junk_id = _upload(client, token, "debug-temp.log", b"ok\n")
        _age_files(retention)

        result = retention.audit_storage(force=True)
        assert result["ran"] is True
        assert result["deleted"] >= 1

        with retention._db() as c:
            assert c.execute("SELECT 1 FROM janus_files WHERE id=?", (useful_id,)).fetchone() is not None
            assert c.execute("SELECT 1 FROM janus_files WHERE id=?", (junk_id,)).fetchone() is None
            rows = c.execute("SELECT decision,reason FROM janus_file_audit_log ORDER BY id").fetchall()
            assert any(r["decision"] == "keep" for r in rows)
            assert any(r["decision"] == "delete" for r in rows)


def test_duplicate_pruning_is_account_local_and_preserves_one_canonical_copy():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        auth, attachment_api, retention = _fresh(tmp)
        client = _client(auth, attachment_api)
        token_a = _register(client, "dupea", "dupea@example.com")
        token_b = _register(client, "dupeb", "dupeb@example.com")
        content = ("shared but meaningful text " * 50).encode()

        a1 = _upload(client, token_a, "copy-one.txt", content)
        time.sleep(0.01)
        a2 = _upload(client, token_a, "copy-two.txt", content)
        b1 = _upload(client, token_b, "independent.txt", content)
        _age_files(retention)

        result = retention.audit_storage(force=True)
        assert result["ran"] is True
        with retention._db() as c:
            aid = c.execute("SELECT id FROM accounts WHERE username='dupea'").fetchone()[0]
            bid = c.execute("SELECT id FROM accounts WHERE username='dupeb'").fetchone()[0]
            a_rows = c.execute("SELECT id FROM janus_files WHERE account_id=?", (aid,)).fetchall()
            b_rows = c.execute("SELECT id FROM janus_files WHERE account_id=?", (bid,)).fetchall()
            assert len(a_rows) == 1
            assert a_rows[0]["id"] in {a1, a2}
            assert len(b_rows) == 1
            assert b_rows[0]["id"] == b1


def test_pinned_files_are_never_autonomously_deleted():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        auth, attachment_api, retention = _fresh(tmp)
        client = _client(auth, attachment_api)
        token = _register(client, "pinuser", "pin@example.com")
        file_id = _upload(client, token, "debug-temp.log", b"x")
        retention.init_retention_schema()
        old = int(time.time()) - 60 * 86400
        with retention._db() as c:
            c.execute("UPDATE janus_files SET pinned=1,created_at=?,last_touched_at=? WHERE id=?", (old, old, file_id))
        retention.audit_storage(force=True)
        with retention._db() as c:
            assert c.execute("SELECT 1 FROM janus_files WHERE id=?", (file_id,)).fetchone() is not None
