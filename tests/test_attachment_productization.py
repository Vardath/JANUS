import importlib
import sqlite3
from pathlib import Path

import pytest
from fastapi import HTTPException


def load(tmp_path, monkeypatch):
    db = tmp_path / "janus.sqlite3"
    files = tmp_path / "files"
    monkeypatch.setenv("JANUS_DB_PATH", str(db))
    monkeypatch.setenv("JANUS_AUTH_DB", str(db))
    monkeypatch.setenv("JANUS_FILE_DIR", str(files))
    import auth, document_grounding, attachment_api, attachment_chat
    auth = importlib.reload(auth)
    document_grounding = importlib.reload(document_grounding)
    attachment_api = importlib.reload(attachment_api)
    attachment_chat = importlib.reload(attachment_chat)
    return db, files, auth, attachment_api, attachment_chat


def add_account(db: Path, username: str, email: str) -> dict:
    with sqlite3.connect(db) as c:
        cur = c.execute(
            "INSERT INTO accounts(username,email,password_hash,created_at,updated_at,email_verified) VALUES(?,?,?,1,1,1)",
            (username, email, "test"),
        )
        aid = int(cur.lastrowid)
    return {"id": aid, "username": username, "email": email}


def test_attachment_ids_are_deduplicated_and_bounded(tmp_path, monkeypatch):
    _, _, _, _, attachment_chat = load(tmp_path, monkeypatch)
    assert attachment_chat._attachment_ids({"attachment_ids": ["a", "a", {"id": "b"}]}) == ["a", "b"]
    too_many = [f"f{i}" for i in range(attachment_chat.MAX_ATTACHMENTS_PER_TURN + 1)]
    with pytest.raises(HTTPException) as exc:
        attachment_chat._attachment_ids({"attachment_ids": too_many})
    assert exc.value.status_code == 400


def test_stored_attachment_is_account_bound_and_groundable(tmp_path, monkeypatch):
    db, _, _, attachment_api, attachment_chat = load(tmp_path, monkeypatch)
    alice = add_account(db, "alice", "alice@example.test")
    bob = add_account(db, "bob", "bob@example.test")

    meta = attachment_api.store_generated_file(
        alice["id"],
        "evidence.txt",
        b"JANUS attachment grounding marker: alpha beta gamma",
        "text/plain",
    )
    items, grounding = attachment_chat._load_grounding(
        alice["id"], [meta["id"]], query="What does the attached evidence say?"
    )
    assert items and items[0]["id"] == meta["id"]
    assert items[0]["grounded"] is True
    assert "alpha beta gamma" in grounding

    with pytest.raises(HTTPException) as exc:
        attachment_chat._file_rows(bob["id"], [meta["id"]])
    assert exc.value.status_code == 404


def test_attachment_grounding_is_published_to_all_specialists(tmp_path, monkeypatch):
    _, _, _, _, attachment_chat = load(tmp_path, monkeypatch)

    class Cycle:
        def __init__(self):
            self.sent = []
            self.bursts = 0
        def send(self, sender, target, content, kind):
            self.sent.append((sender, target, content, kind))
        def service_work_burst(self, **kwargs):
            self.bursts += 1

    cycle = Cycle()
    attachment_chat._publish_specialist_grounding(cycle, "SOURCE DOCUMENT: evidence.txt\nimportant marker", "document_grounding")
    targets = {row[1] for row in cycle.sent}
    assert targets == {"evidence", "logic", "counterpoint", "context", "memory", "novelty", "safety"}
    assert cycle.bursts == 1


def test_android_attachment_patch_keeps_complete_product_path():
    text = Path("tools/patch_android_file_attachments.py").read_text(encoding="utf-8")
    required = (
        "RC_FILE_PICKER",
        "Android.pickFile()",
        "/files/upload",
        "pendingAttachments",
        "attachment_ids:atts.map(x=>x.id)",
        "Up to 4 files can be attached",
        "Attachment upload failed",
        "Please assess the attached file or files.",
    )
    missing = [needle for needle in required if needle not in text]
    assert not missing, f"Android attachment workflow regressed; missing: {missing}"


def test_android_build_applies_attachment_patch_before_consolidated_runtime():
    workflow = Path(".github/workflows/build-android.yml").read_text(encoding="utf-8")
    attachment = workflow.index("python tools/patch_android_file_attachments.py")
    consolidated = workflow.index("python tools/patch_android_runtime_cores_v068.py")
    assert attachment < consolidated
