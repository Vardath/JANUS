from __future__ import annotations

import hashlib
import os
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

root = Path(tempfile.mkdtemp(prefix="janus-v2-session-"))
db_path = root / "janus.sqlite3"
os.environ["JANUS_DB_PATH"] = str(db_path)
os.environ["JANUS_FILE_ROOT"] = str(root / "files")
os.environ.pop("OPENAI_API_KEY", None)

legacy_token = "existing-native-client-session-token"
token_hash = hashlib.sha256(legacy_token.encode("utf-8")).hexdigest()
now = int(time.time())

with sqlite3.connect(db_path) as c:
    c.execute("CREATE TABLE accounts(id INTEGER PRIMARY KEY,username TEXT,email TEXT,password_hash TEXT,created_at INTEGER,updated_at INTEGER,disabled INTEGER DEFAULT 0,google_sub TEXT,email_verified INTEGER DEFAULT 0)")
    c.execute("INSERT INTO accounts VALUES(1,'owner','owner@example.com','google_only',?,?,?,?,?)", (now-1000, now-1000, 0, None, 1))
    c.execute("CREATE TABLE sessions(token_hash TEXT PRIMARY KEY,account_id INTEGER NOT NULL,created_at INTEGER NOT NULL,expires_at INTEGER NOT NULL)")
    c.execute("INSERT INTO sessions VALUES(?,?,?,?)", (token_hash, 1, now-500, now+86400))

from server_v2.entrypoint import app, MIGRATION_RESULT
from fastapi.testclient import TestClient

assert MIGRATION_RESULT.get("accounts") == 1, MIGRATION_RESULT
assert MIGRATION_RESULT.get("sessions") == 1, MIGRATION_RESULT

with TestClient(app) as client:
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {legacy_token}"})
    assert r.status_code == 200, r.text
    assert r.json()["account"]["username"] == "owner"

print("JANUS server v2 session cutover verification passed: an already signed-in native client remains authenticated after data-only migration.")
