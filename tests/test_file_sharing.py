import base64
import importlib
import os
import tempfile
from pathlib import Path


def _fresh_modules(tmp: Path):
    os.environ["JANUS_DB_PATH"] = str(tmp / "janus.sqlite3")
    os.environ["JANUS_AUTH_DB"] = str(tmp / "janus.sqlite3")
    os.environ["JANUS_FILE_DIR"] = str(tmp / "files")
    import auth
    import attachment_api
    importlib.reload(auth)
    importlib.reload(attachment_api)
    return auth, attachment_api


def test_account_bound_upload_list_download_delete():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        auth, attachment_api = _fresh_modules(tmp)
        app = FastAPI()
        app.include_router(auth.router)
        app.include_router(attachment_api.router)
        client = TestClient(app)

        r = client.post("/auth/register", json={"username": "fileuser", "email": "file@example.com", "password": "password12345"})
        assert r.status_code == 200, r.text
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        content = b"JANUS attachment grounding\nsecond line\n"
        r = client.post("/files/upload", headers=headers, json={
            "filename": "notes.txt",
            "mime_type": "text/plain",
            "data_base64": base64.b64encode(content).decode("ascii"),
        })
        assert r.status_code == 200, r.text
        item = r.json()["file"]
        assert item["filename"] == "notes.txt"
        assert item["size_bytes"] == len(content)
        assert item["has_extracted_text"] is True
        file_id = item["id"]

        r = client.get("/files", headers=headers)
        assert r.status_code == 200
        assert [x["id"] for x in r.json()["items"]] == [file_id]

        r = client.get(f"/files/{file_id}/download", headers=headers)
        assert r.status_code == 200
        assert r.content == content

        other = client.post("/auth/register", json={"username": "otheruser", "email": "other@example.com", "password": "password12345"}).json()["access_token"]
        r = client.get(f"/files/{file_id}", headers={"Authorization": f"Bearer {other}"})
        assert r.status_code == 404

        r = client.delete(f"/files/{file_id}", headers=headers)
        assert r.status_code == 200
        assert not any((tmp / "files").iterdir())


def test_rejects_unsupported_extension_and_bad_base64():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        auth, attachment_api = _fresh_modules(tmp)
        app = FastAPI()
        app.include_router(auth.router)
        app.include_router(attachment_api.router)
        client = TestClient(app)
        token = client.post("/auth/register", json={"username": "guarduser", "email": "guard@example.com", "password": "password12345"}).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        r = client.post("/files/upload", headers=headers, json={"filename": "payload.exe", "mime_type": "application/octet-stream", "data_base64": "YWJj"})
        assert r.status_code == 415

        r = client.post("/files/upload", headers=headers, json={"filename": "notes.txt", "mime_type": "text/plain", "data_base64": "%%%not-base64%%%"})
        assert r.status_code == 400
