import asyncio
import hashlib
import importlib
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock


def _fresh(tmp: Path):
    os.environ["JANUS_DB_PATH"] = str(tmp / "janus.sqlite3")
    os.environ["JANUS_AUTH_DB"] = str(tmp / "janus.sqlite3")
    os.environ["JANUS_FILE_DIR"] = str(tmp / "files")
    os.environ["OPENAI_API_KEY"] = "test-key"
    import auth
    import attachment_api
    import vision_analysis
    importlib.reload(auth)
    importlib.reload(attachment_api)
    importlib.reload(vision_analysis)
    return auth, attachment_api, vision_analysis


def _make_account(auth, username: str, email: str) -> int:
    auth._init_db()
    with auth._db() as c:
        c.execute(
            "INSERT INTO accounts(username,email,password_hash,created_at) VALUES(?,?,?,?)",
            (username, email, "x", 1),
        )
        return int(c.execute("SELECT id FROM accounts WHERE username=?", (username,)).fetchone()[0])


def _make_image(attachment_api, account_id: int, file_id: str, data: bytes, name: str = "sample.jpg"):
    attachment_api._init_db()
    storage_name = f"{account_id}-{file_id}.jpg"
    attachment_api.FILE_ROOT.mkdir(parents=True, exist_ok=True)
    (attachment_api.FILE_ROOT / storage_name).write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    with attachment_api._db() as c:
        c.execute(
            """INSERT INTO janus_files(id,account_id,original_name,mime_type,size_bytes,sha256,storage_name,extracted_text,extraction_status,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (file_id, account_id, name, "image/jpeg", len(data), digest, storage_name, None, "not_applicable", 1),
        )
    return digest


def test_first_analysis_is_cached_and_reused_without_second_model_call():
    with tempfile.TemporaryDirectory() as td:
        auth, attachment_api, vision = _fresh(Path(td))
        account_id = _make_account(auth, "visiona", "visiona@example.com")
        _make_image(attachment_api, account_id, "img1", b"image-bytes-one")
        vision._call_model = AsyncMock(return_value="A screenshot with a settings panel and readable status text.")

        first = asyncio.run(vision.assess_images(account_id, ["img1"], "Please assess this image"))
        second = asyncio.run(vision.assess_images(account_id, ["img1"], "What does it show?"))

        assert first["img1"]["status"] == "analyzed"
        assert second["img1"]["status"] == "cached"
        assert "settings panel" in second["img1"]["assessment"]
        assert vision._call_model.await_count == 1


def test_visual_cache_is_not_shared_across_accounts():
    with tempfile.TemporaryDirectory() as td:
        auth, attachment_api, vision = _fresh(Path(td))
        a = _make_account(auth, "visionb", "visionb@example.com")
        b = _make_account(auth, "visionc", "visionc@example.com")
        data = b"same-image-bytes"
        _make_image(attachment_api, a, "imga", data)
        _make_image(attachment_api, b, "imgb", data)
        vision._call_model = AsyncMock(side_effect=["assessment A", "assessment B"])

        ra = asyncio.run(vision.assess_images(a, ["imga"], "assess"))
        rb = asyncio.run(vision.assess_images(b, ["imgb"], "assess"))

        assert ra["imga"]["status"] == "analyzed"
        assert rb["imgb"]["status"] == "analyzed"
        assert vision._call_model.await_count == 2


def test_account_cleanup_removes_cached_assessments_and_usage():
    with tempfile.TemporaryDirectory() as td:
        auth, attachment_api, vision = _fresh(Path(td))
        account_id = _make_account(auth, "visiond", "visiond@example.com")
        _make_image(attachment_api, account_id, "img1", b"image-bytes-cleanup")
        vision._call_model = AsyncMock(return_value="cached assessment")
        asyncio.run(vision.assess_images(account_id, ["img1"], "assess"))
        assert vision.cleanup_account(account_id) >= 2
        with vision._db() as c:
            assert c.execute("SELECT COUNT(*) FROM janus_visual_assessment_cache WHERE account_id=?", (account_id,)).fetchone()[0] == 0
            assert c.execute("SELECT COUNT(*) FROM janus_visual_usage WHERE account_id=?", (account_id,)).fetchone()[0] == 0
