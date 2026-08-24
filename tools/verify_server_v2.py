from __future__ import annotations

import base64
import hashlib
import importlib
import os
import secrets
import sqlite3
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

root = Path(tempfile.mkdtemp(prefix="janus-v2-verify-"))
db_path = root / "janus.sqlite3"
file_root = root / "files"
os.environ["JANUS_DB_PATH"] = str(db_path)
os.environ["JANUS_FILE_ROOT"] = str(file_root)
os.environ["JANUS_EMAIL_MODE"] = "development"
os.environ.pop("OPENAI_API_KEY", None)

# Persistence fixture deliberately contains the old mechanical description so the
# migration test proves old user memory is preserved rather than rewritten.
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
    c.execute("INSERT INTO desktop_events VALUES(1,'owner','checkpoint','Persistence fixture','2026-08-20T00:00:00+00:00')")

entry = importlib.import_module("server_v2.entrypoint")
app = entry.app
from server_v2.mind import mind
from server_v2.runtime_persistence import runtime_persistence
from server_v2.topology import CORE_NAMES, FRONT_CORE

assert len(CORE_NAMES) == 11
assert FRONT_CORE == "front"

# Keep verification offline while exercising the complete sensory route.
mind._model_reply = lambda *args, **kwargs: "Verified JANUS interface response."
mind.web_research = lambda query, account_id=None, governed=True: ("", [])

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

    login = client.post("/auth/login", json={"identifier": "owner", "password": password})
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    me = client.get("/auth/me", headers=headers)
    assert me.status_code == 200 and me.json()["account"]["username"] == "owner"

    identity = client.get("/desktop/identity-core", headers=headers)
    assert identity.status_code == 200, identity.text
    ic = identity.json()["identity_core"]
    assert identity.json()["protected"] is True
    assert identity.json()["ordinary_conversation_can_overwrite"] is False
    assert "1|3|7" in ic["architecture"] and "Front/Bridge" in ic["architecture"]

    memory = client.get("/desktop/memory?username=forged", headers=headers)
    assert memory.status_code == 200 and memory.json()["profile"] == "owner"
    assert any("7 -> 2 -> 1 -> 1" in x["content"] for x in memory.json()["items"])

    chat = client.post("/desktop/chat", headers=headers, json={
        "profile_id": "forged", "username": "forged",
        "message": "Explain the active architecture.", "client_message_id": "verify-1",
    })
    assert chat.status_code == 200, chat.text
    body = chat.json()
    assert body["profile"] == "owner"
    assert body["route_trace"] == list(CORE_NAMES)
    assert body["route_trace"][-2:] == ["front", "interface"]
    assert body["reply"] == "Verified JANUS interface response."
    assert "1-3-7" in body["architecture"]
    assert body["mechanical_flow"] == "7 -> 2 -> 1 -> 1"
    assert set(body["bridge_authority"].keys()) == {"left", "right"}
    assert set(body["front"]["appraisal"]) >= {"confidence", "valence", "uncertainty", "risk", "opportunity", "conflict"}
    assert body["model_policy"]["selected_model"].startswith("gpt-5.6-")

    # Chat receipts remain account-bound and idempotent.
    again = client.post("/desktop/chat", headers=headers, json={"message": "different text", "client_message_id": "verify-1"})
    assert again.status_code == 200 and again.json()["reply"] == body["reply"]

    # Legacy local clients may still send consensus; server maps it to canonical Front
    # and returns both the canonical field and a temporary compatibility alias.
    sync = client.post("/core-sync/exchange", headers=headers, json={
        "device_id": "verify-device", "client_version": "v1.08", "phase": "wake",
        "consensus": "legacy local front state", "interface": "local interface",
        "observe_events": [{"detail": "local specialist summary"}],
    })
    assert sync.status_code == 200, sync.text
    sj = sync.json()
    assert sj["guidance"]["sync_policy"] == "selective-no-overwrite"
    assert sj["guidance"]["peer_policy"] == "peer-state-reenters-through-all-seven-senses"
    assert sj["server"]["core_count"] == 11
    assert sj["server"]["conceptual_topology"] == "1|3|7"
    assert sj["server"]["mechanical_flow"] == "7 -> 2 -> 1 -> 1"
    assert sj["server"]["front"] == sj["server"]["consensus"]
    assert "front_appraisal" in sj["server"] and "interface_appraisal" in sj["server"]

    runtime = client.get("/desktop/runtime-cores?username=forged", headers=headers)
    assert runtime.status_code == 200
    rt = runtime.json()["runtime"]
    assert rt["core_count"] == 11 and rt["registered_clients"] == 1
    assert rt["conceptual_topology"] == "1|3|7"
    assert set(CORE_NAMES).issubset(rt["cores"])
    assert rt["cores"]["consensus"]["alias_for"] == "front"
    assert len(rt["core_reliability"]) == 11
    assert rt["bridge_authority"]

    reliability = client.get("/reliability/status", headers=headers)
    assert reliability.status_code == 200
    assert reliability.json()["authority_bounds"] == [0.2, 0.8]

    upload = client.post("/files/upload", headers=headers, json={
        "filename": "notes.txt", "mime_type": "text/plain",
        "data_base64": base64.b64encode(b"Evidence from a clean file pipeline.").decode(),
    })
    assert upload.status_code == 200, upload.text
    fid = upload.json()["file"]["id"]
    grounded = client.post("/desktop/chat", headers=headers, json={
        "message": "Assess the attached note.", "attachment_ids": [fid], "client_message_id": "verify-file"
    })
    assert grounded.status_code == 200 and grounded.json()["attachment_grounding"] is True

    continuity = client.post("/desktop/continuity", headers=headers, json={"title": "Verify federated runtime", "detail": "Keep local/global sync selective", "priority": 90})
    assert continuity.status_code == 200, continuity.text
    cid = continuity.json()["item"]["id"]
    moved = client.post(f"/desktop/continuity/{cid}/state", headers=headers, json={"state": "active", "note": "verification"})
    assert moved.status_code == 200 and moved.json()["item"]["state"] == "active"

    seed = client.post("/research/workspace/seed", headers=headers)
    assert seed.status_code == 200
    ws = client.get("/research/workspace", headers=headers)
    assert ws.status_code == 200 and ws.json()["count"] >= 3
    claim = client.post("/claims", headers=headers, json={"title": "Test claim", "statement": "Clean v2 sensory route exists"})
    assert claim.status_code == 200
    claim_id = claim.json()["claim"]["id"]
    ev = client.post(f"/claims/{claim_id}/evidence", headers=headers, json={"summary": "Verified by integration test"})
    assert ev.status_code == 200

    artifact = client.post("/artifacts", headers=headers, json={"kind": "continuity_report"})
    assert artifact.status_code == 200, artifact.text
    artifact_id = artifact.json()["artifact"]["id"]
    info = client.get(f"/artifacts/{artifact_id}", headers=headers)
    assert info.status_code == 200 and info.json()["artifact"]["available"] is True

    observe = client.get("/desktop/core-observe?username=forged&limit=300", headers=headers)
    assert observe.status_code == 200 and observe.json()["profile"] == "owner"
    names = {x["core_name"] for x in observe.json()["items"]}
    assert set(CORE_NAMES).issubset(names)
    # Peer feedback is sensed by every subconscious core, not directly injected into Front.
    peer_names = {x["core_name"] for x in observe.json()["items"] if x["event_type"] in {"peer_sense", "peer_observation"}}
    assert {"evidence", "safety", "counterpoint", "context", "logic", "novelty", "memory"}.issubset(peer_names)

    # Durable runtime checkpoints contain exactly eleven canonical cores. Legacy
    # consensus rows are read-compatible but purged after a canonical checkpoint.
    checkpoint_before = mind.status(1)["cores"]["front"]["summary"]
    assert checkpoint_before
    assert runtime_persistence.checkpoint_account(1) == 11
    stored_names = {x["core_name"] for x in __import__("server_v2.storage", fromlist=["rows"]).rows("SELECT core_name FROM v2_runtime_core_state WHERE account_id=?", (1,))}
    assert stored_names == set(CORE_NAMES)
    assert "consensus" not in stored_names
    mind._profiles.pop(1, None)
    assert mind.status(1)["cores"]["front"]["summary"] == ""
    restored = runtime_persistence.restore_all()
    assert restored["profiles"] >= 1 and restored["cores"] >= 11
    assert mind.status(1)["cores"]["front"]["summary"] == checkpoint_before

    # A second account cannot select, read, download or observe the owner's state.
    second = client.post("/auth/register", json={"username": "second-user", "email": "second@example.com", "password": "AnotherPassword12345"})
    assert second.status_code == 200, second.text
    h2 = {"Authorization": "Bearer " + second.json()["access_token"]}
    m2 = client.get("/desktop/memory?username=owner", headers=h2)
    assert m2.status_code == 200 and m2.json()["profile"] == "second-user"
    assert not any("Preserve JANUS" in x["content"] for x in m2.json()["items"])
    o2 = client.get("/desktop/core-observe?username=owner&limit=200", headers=h2)
    assert o2.status_code == 200 and o2.json()["profile"] == "second-user"
    assert all("local specialist summary" not in x["detail"] for x in o2.json()["items"])
    forbidden = client.get(f"/files/{fid}/download", headers=h2)
    assert forbidden.status_code == 404
    r2 = client.get("/desktop/runtime-cores?username=owner", headers=h2).json()["runtime"]
    assert r2["registered_clients"] == 0
    assert r2["cores"]["front"]["summary"] == ""

    # Only the owner account can make maintenance decisions.
    with sqlite3.connect(db_path) as c:
        c.execute("INSERT INTO v2_maintenance(account_id,report_json,review_state,created_at) VALUES(1,'{}','awaiting_owner_review',1700000000)")
    review_id = client.get("/maintenance/status", headers=headers).json()["reviews"][0]["id"]
    denied = client.post(f"/maintenance/reviews/{review_id}/decision", headers=h2, json={"decision": "deferred"})
    assert denied.status_code == 403
    allowed = client.post(f"/maintenance/reviews/{review_id}/decision", headers=headers, json={"decision": "deferred"})
    assert allowed.status_code == 200

print("JANUS server v2 verification passed: canonical 1|3|7 sensory routing, exactly eleven durable cores, Front migration, selective federation, protected identity, bounded appraisals, files, research and owner-gated maintenance.")
