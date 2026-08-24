from __future__ import annotations

import hashlib
import hmac
import importlib
import os
import secrets
import sqlite3
import tempfile
from pathlib import Path

root = Path(tempfile.mkdtemp(prefix="janus-v2-verify-"))
db_path = root / "janus.sqlite3"
file_root = root / "files"
os.environ["JANUS_DB_PATH"] = str(db_path)
os.environ["JANUS_FILE_ROOT"] = str(file_root)
os.environ["JANUS_EMAIL_MODE"] = "development"
os.environ.pop("OPENAI_API_KEY", None)

# Build a tiny legacy-data fixture. The new code may read persisted records but
# must not import or execute legacy server modules.
salt = secrets.token_bytes(16)
iterations = 600_000
password = "TestPassword12345"
digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
legacy_hash = f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"
with sqlite3.connect(db_path) as c:
    c.execute("CREATE TABLE accounts(id INTEGER PRIMARY KEY,username TEXT,email TEXT,password_hash TEXT,created_at INTEGER,updated_at INTEGER,disabled INTEGER DEFAULT 0,google_sub TEXT,email_verified INTEGER DEFAULT 0)")
    c.execute("INSERT INTO accounts VALUES(1,'owner','owner@example.com',?,1700000000,1700000000,0,NULL,1)", (legacy_hash,))
    c.execute("CREATE TABLE desktop_memory(id INTEGER PRIMARY KEY,profile_id TEXT,role TEXT,content TEXT,level TEXT,created_at TEXT)")
    c.execute("INSERT INTO desktop_memory VALUES(1,'owner','user','Preserve JANUS 7 -> 2 -> 1 -> 1 continuity.','core','2026-08-20T00:00:00+00:00')")
    c.execute("CREATE TABLE desktop_events(id INTEGER PRIMARY KEY,profile_id TEXT,event_type TEXT,detail TEXT,created_at TEXT)")
    c.execute("INSERT INTO desktop_events VALUES(1,'owner','checkpoint','Legacy persistence fixture','2026-08-20T00:00:00+00:00')")

entry = importlib.import_module("server_v2.entrypoint")
app = entry.app
from server_v2.mind import mind

# Keep verification offline while still exercising the complete 7->2->1->1 route.
mind._model_reply = lambda message, consensus, memories, evidence, web_context="": "Verified JANUS interface response."
mind.web_research = lambda query: ("", [])

from fastapi.testclient import TestClient

with TestClient(app) as client:
    h = client.get("/health")
    assert h.status_code == 200, h.text
    assert h.json()["core_count"] == 11

    caps = client.get("/protocol/capabilities")
    assert caps.status_code == 200
    assert caps.json()["server_generation"] == "v2-clean-reconstruction"
    for key in ("chat", "messages", "observe", "memory", "local_global_sync", "attachments", "visual_analysis", "foreground_web", "research_workspace", "artifacts", "image_generation", "maintenance"):
        assert caps.json()["features"].get(key) is True, key

    # Legacy account data has been copied into the new schema. The first successful
    # login upgrades the password hash without running legacy authentication code.
    login = client.post("/auth/login", json={"identifier":"owner", "password":password})
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = client.get("/auth/me", headers=headers)
    assert me.status_code == 200 and me.json()["account"]["username"] == "owner"

    memory = client.get("/desktop/memory?username=forged", headers=headers)
    assert memory.status_code == 200
    assert memory.json()["profile"] == "owner"
    assert any("7 -> 2 -> 1 -> 1" in x["content"] for x in memory.json()["items"])

    chat = client.post("/desktop/chat", headers=headers, json={
        "profile_id":"forged",
        "username":"forged",
        "message":"Explain the active architecture.",
        "client_message_id":"verify-1",
    })
    assert chat.status_code == 200, chat.text
    body = chat.json()
    assert body["profile"] == "owner"
    assert body["route_trace"] == ["evidence","logic","counterpoint","context","memory","safety","novelty","left_hemisphere","right_hemisphere","consensus","interface"]
    assert body["reply"] == "Verified JANUS interface response."

    # Idempotent receipt.
    again = client.post("/desktop/chat", headers=headers, json={"message":"different text", "client_message_id":"verify-1"})
    assert again.status_code == 200 and again.json()["reply"] == body["reply"]

    sync = client.post("/core-sync/exchange", headers=headers, json={
        "device_id":"verify-device", "client_version":"v0.82", "phase":"wake",
        "observe_events":[{"detail":"local specialist summary"}],
    })
    assert sync.status_code == 200
    assert sync.json()["guidance"]["sync_policy"] == "selective-no-overwrite"

    runtime = client.get("/desktop/runtime-cores?username=forged", headers=headers)
    assert runtime.status_code == 200
    rt = runtime.json()["runtime"]
    assert rt["core_count"] == 11 and rt["registered_clients"] == 1

    import base64
    upload = client.post("/files/upload", headers=headers, json={
        "filename":"notes.txt", "mime_type":"text/plain",
        "data_base64":base64.b64encode(b"Evidence from a clean file pipeline.").decode(),
    })
    assert upload.status_code == 200, upload.text
    fid = upload.json()["file"]["id"]
    grounded = client.post("/desktop/chat", headers=headers, json={
        "message":"Assess the attached note.", "attachment_ids":[fid], "client_message_id":"verify-file"
    })
    assert grounded.status_code == 200 and grounded.json()["attachment_grounding"] is True

    seed = client.post("/research/workspace/seed", headers=headers)
    assert seed.status_code == 200
    ws = client.get("/research/workspace", headers=headers)
    assert ws.status_code == 200 and ws.json()["count"] >= 3

    artifact = client.post("/artifacts", headers=headers, json={"kind":"continuity_report"})
    assert artifact.status_code == 200, artifact.text
    aid = artifact.json()["artifact"]["id"]
    info = client.get(f"/artifacts/{aid}", headers=headers)
    assert info.status_code == 200 and info.json()["artifact"]["available"] is True

    observe = client.get("/desktop/core-observe?username=forged&limit=200", headers=headers)
    assert observe.status_code == 200
    assert observe.json()["profile"] == "owner"
    names = {x["core_name"] for x in observe.json()["items"]}
    assert set(("evidence","logic","counterpoint","context","memory","safety","novelty","left_hemisphere","right_hemisphere","consensus","interface")).issubset(names)

print("JANUS server v2 verification passed: clean auth, persistence migration, 11-core routing, sync, files, research and artifacts.")
