import importlib
import os
import sqlite3
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _fresh(tmp: Path):
    os.environ["JANUS_DB_PATH"] = str(tmp / "janus.sqlite3")
    os.environ["JANUS_AUTH_DB"] = str(tmp / "janus.sqlite3")
    os.environ["JANUS_CLIENT_PRESENCE_TTL_SECONDS"] = "30"
    import auth
    import federated_sync
    import core_sync
    auth = importlib.reload(auth)
    federated_sync = importlib.reload(federated_sync)
    core_sync = importlib.reload(core_sync)
    return auth, federated_sync, core_sync


def _client(tmp: Path):
    auth, federated_sync, core_sync = _fresh(tmp)
    app = FastAPI()
    app.include_router(auth.router)
    app.include_router(core_sync.router)
    return TestClient(app), auth, federated_sync, core_sync


def _register(client, username="syncuser", email="sync@example.test"):
    r = client.post("/auth/register", json={"username": username, "email": email, "password": "password12345"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _exchange(client, token, device_id, cycles=None, sync_records=None):
    return client.post(
        "/core-sync/exchange",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "device_id": device_id,
            "platform": "android",
            "client_version": "soak",
            "phase": "wake",
            "cycles": cycles or {},
            "observe_events": [],
            "memories": [],
            "conclusions": [],
            "sync_records": sync_records or [],
        },
    )


def test_reconnect_same_device_updates_presence_without_duplicate_registration(tmp_path):
    client, _, _, _ = _client(tmp_path)
    token = _register(client)
    for n in range(12):
        r = _exchange(client, token, "phone", {"evidence": n, "interface": n + 3})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["presence"]["registered"] == 1
        assert body["presence"]["online"] == 1
    status = client.get("/core-sync/status", headers={"Authorization": f"Bearer {token}"}).json()
    assert status["registered_clients"] == 1
    assert status["clients"][0]["cycles"]["evidence"] == 11


def test_stale_heartbeat_becomes_offline_then_recovers_without_losing_registration(tmp_path):
    client, _, _, core_sync = _client(tmp_path)
    token = _register(client)
    assert _exchange(client, token, "phone", {"logic": 4}).status_code == 200
    with sqlite3.connect(os.environ["JANUS_DB_PATH"]) as c:
        c.execute("UPDATE janus_client_presence SET last_seen_at=last_seen_at-120 WHERE device_id='phone'")
        c.commit()
    stale = client.get("/core-sync/status", headers={"Authorization": f"Bearer {token}"}).json()
    assert stale["registered_clients"] == 1
    assert stale["remote_clients"] == 0
    assert stale["clients"][0]["online"] is False
    recovered = _exchange(client, token, "phone", {"logic": 5}).json()
    assert recovered["presence"]["registered"] == 1
    assert recovered["presence"]["online"] == 1
    assert recovered["presence"]["clients"][0]["cycles"]["logic"] == 5


def test_two_devices_exchange_selective_records_without_echo_or_whole_state_overwrite(tmp_path):
    client, _, _, _ = _client(tmp_path)
    token = _register(client)
    a = _exchange(client, token, "phone", sync_records=[{
        "origin_id": "m1", "kind": "memory", "text": "Keep local project state authoritative while sharing this grounding note.", "confidence": 0.8
    }]).json()
    assert a["federated_sync"]["accepted"] == 1
    assert a["shared_state"]["federated_records"] == []
    b = _exchange(client, token, "tablet").json()
    records = b["shared_state"]["federated_records"]
    assert len(records) == 1
    assert records[0]["origin_device"] == "phone"
    assert records[0]["merge_policy"] == "grounding_only_no_overwrite"
    assert "no_whole_state_overwrite" in b["shared_state"]["policy"]


def test_conflicting_device_claims_remain_both_present_and_conflicted(tmp_path):
    client, _, federated_sync, _ = _client(tmp_path)
    token = _register(client)
    r1 = _exchange(client, token, "phone", sync_records=[{
        "origin_id": "q-phone", "kind": "question", "text": "Investigate passive code local energy barrier", "state": "investigating", "confidence": 0.7
    }])
    assert r1.status_code == 200
    r2 = _exchange(client, token, "tablet", sync_records=[{
        "origin_id": "q-tablet", "kind": "question", "text": "Investigate passive code local energy barrier", "state": "resolved", "confidence": 0.9
    }])
    assert r2.status_code == 200
    assert r2.json()["federated_sync"]["conflicts"] >= 1
    records = federated_sync.outbound("syncuser", "laptop", 10)
    assert len(records) == 2
    assert all(x["text"] == "Investigate passive code local energy barrier" for x in records)
    assert any(x["state"] == "investigating" for x in records)
    assert any(x["state"] == "resolved" for x in records)
    assert any(x["status"] == "conflicted" for x in records)


def test_repeated_restart_and_reconnect_preserves_selective_records(tmp_path):
    client, _, _, _ = _client(tmp_path)
    token = _register(client)
    assert _exchange(client, token, "phone", sync_records=[{
        "origin_id": "project-1", "kind": "project", "text": "Selective sync soak project remains locally authoritative.", "state": "active"
    }]).status_code == 200

    for n in range(8):
        # Simulate a server process restart by reloading the persistence-facing modules
        # against the same database, then reconnect the same authenticated device.
        import federated_sync
        import core_sync
        importlib.reload(federated_sync)
        importlib.reload(core_sync)
        rows = federated_sync.outbound("syncuser", "tablet", 10)
        assert len(rows) == 1
        assert rows[0]["origin_id"] == "project-1"
        assert rows[0]["merge_policy"] == "grounding_only_no_overwrite"

    # Reconnecting with the same stable origin id updates in place rather than cloning.
    updated = _exchange(client, token, "phone", sync_records=[{
        "origin_id": "project-1", "kind": "project", "text": "Selective sync soak project remains locally authoritative.", "state": "testing"
    }]).json()
    assert updated["federated_sync"]["updated"] == 1
    rows = __import__("federated_sync").outbound("syncuser", "tablet", 10)
    assert len(rows) == 1
    assert rows[0]["state"] == "testing"
