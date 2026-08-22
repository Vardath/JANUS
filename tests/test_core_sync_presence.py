import importlib
import os
import tempfile
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _fresh(tmp: Path):
    os.environ["JANUS_DB_PATH"] = str(tmp / "janus.sqlite3")
    os.environ["JANUS_AUTH_DB"] = str(tmp / "janus.sqlite3")
    import auth
    import core_sync
    importlib.reload(auth)
    importlib.reload(core_sync)
    return auth, core_sync


def _register(client, username, email):
    r = client.post("/auth/register", json={"username": username, "email": email, "password": "password12345"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_presence_is_authenticated_account_bound_and_live():
    with tempfile.TemporaryDirectory() as td:
        auth, core_sync = _fresh(Path(td))
        app = FastAPI()
        app.include_router(auth.router)
        app.include_router(core_sync.router)
        client = TestClient(app)
        token = _register(client, "presence1", "presence1@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "device_id": "android-test-device",
            "platform": "android",
            "client_version": "0.54",
            "phase": "wake",
            "cycles": {"evidence": 12, "interface": 20},
            "observe_events": [],
            "memories": ["useful local memory"],
            "conclusions": ["tentative local conclusion"],
        }
        r = client.post("/core-sync/exchange", headers=headers, json=payload)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["presence"]["online"] == 1
        assert body["presence"]["registered"] == 1
        assert body["presence"]["clients"][0]["platform"] == "android"
        # Step 3 strengthened the original tagged-grounding policy. Preserve that
        # invariant rather than pinning this regression test to the older exact text.
        policy = body["shared_state"]["policy"]
        assert "tagged_grounding_only" in policy
        assert "no_whole_state_overwrite" in policy
        assert isinstance(body["shared_state"].get("federated_records"), list)
        assert body["sync_policy"].startswith("selective typed records")

        r = client.get("/core-sync/status", headers=headers)
        assert r.status_code == 200
        status = r.json()
        assert status["remote_clients"] == 1
        assert status["registered_clients"] == 1
        assert status["clients"][0]["cycles"]["evidence"] == 12
        assert status["persistent_storage"] in (True, False)
        assert "no whole-state overwrite" in status["sync_policy"]

        token2 = _register(client, "presence2", "presence2@example.com")
        r = client.get("/core-sync/status", headers={"Authorization": f"Bearer {token2}"})
        assert r.status_code == 200
        assert r.json()["registered_clients"] == 0


def test_sync_rejects_unauthenticated_presence():
    with tempfile.TemporaryDirectory() as td:
        auth, core_sync = _fresh(Path(td))
        app = FastAPI()
        app.include_router(auth.router)
        app.include_router(core_sync.router)
        client = TestClient(app)
        r = client.post("/core-sync/exchange", json={"device_id": "x"})
        assert r.status_code == 401
