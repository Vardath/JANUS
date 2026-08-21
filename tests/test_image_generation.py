import importlib
import os
import tempfile
import time
import unittest
from pathlib import Path


def _fresh(tmp: Path):
    os.environ["JANUS_DB_PATH"] = str(tmp / "janus.sqlite3")
    os.environ["JANUS_AUTH_DB"] = str(tmp / "janus.sqlite3")
    os.environ["JANUS_FILE_DIR"] = str(tmp / "files")
    os.environ["JANUS_IMAGE_AUTO_DAILY_CAP"] = "1"
    os.environ["JANUS_IMAGE_AUTO_GLOBAL_DAILY_CAP"] = "20"
    os.environ["JANUS_IMAGE_GLOBAL_DAILY_CAP"] = "100"
    os.environ["JANUS_IMAGE_EXPLICIT_DAILY_CAP"] = "6"
    os.environ["JANUS_IMAGE_AUTO_COOLDOWN_SECONDS"] = "3600"
    import auth
    import attachment_api
    import image_generation
    importlib.reload(auth)
    importlib.reload(attachment_api)
    importlib.reload(image_generation)
    return auth, image_generation


def _account(auth):
    now = int(time.time())
    with auth._db() as c:
        cur = c.execute(
            "INSERT INTO accounts(username,email,password_hash,created_at,updated_at,email_verified) VALUES(?,?,?,?,?,1)",
            ("imageuser", "image@example.com", auth._hash_password("password12345"), now, now),
        )
        return c.execute("SELECT * FROM accounts WHERE id=?", (cur.lastrowid,)).fetchone()


class ImageGenerationPolicyTests(unittest.TestCase):
    def test_explicit_image_intent_and_visual_marker(self):
        with tempfile.TemporaryDirectory() as td:
            _, mod = _fresh(Path(td))
            self.assertTrue(mod.explicit_image_request("Please generate a picture of the topology"))
            self.assertTrue(mod.explicit_image_request("Make me an explanatory diagram"))
            self.assertFalse(mod.explicit_image_request("Explain the topology in words"))
            clean, prompt = mod.extract_visual_nomination("Text first. [[JANUS_VISUAL: a clear Fano plane diagram]]")
            self.assertEqual(clean, "Text first.")
            self.assertEqual(prompt, "a clear Fano plane diagram")

    def test_automatic_budget_stops_repeated_background_renders(self):
        with tempfile.TemporaryDirectory() as td:
            auth, mod = _fresh(Path(td))
            account = _account(auth)
            ok, reason = mod._budget_check(int(account["id"]), "auto", int(time.time()))
            self.assertTrue(ok, reason)
            mod._store_image(int(account["id"]), "first explanatory visual", "low", "1024x1024", "auto", b"fake-png-one")
            ok, reason = mod._budget_check(int(account["id"]), "auto", int(time.time()))
            self.assertFalse(ok)
            self.assertIn("automatic-image", reason)

    def test_same_prompt_is_cacheable_without_another_render(self):
        with tempfile.TemporaryDirectory() as td:
            auth, mod = _fresh(Path(td))
            account = _account(auth)
            prompt = "a compact explanatory diagram of 7 to 2 to 1 to 1"
            stored = mod._store_image(int(account["id"]), prompt, "medium", "1024x1024", "explicit", b"fake-png-two")
            prompt_hash = mod.hashlib.sha256(prompt.encode("utf-8")).hexdigest()
            cached = mod._cached(int(account["id"]), prompt_hash, "medium", "1024x1024")
            self.assertIsNotNone(cached)
            self.assertEqual(cached["file_id"], stored["file_id"])

    def test_background_multicore_rendering_remains_disabled_by_policy(self):
        with tempfile.TemporaryDirectory() as td:
            _, mod = _fresh(Path(td))
            self.assertIn("Multi-core autonomous visual deliberation/render loops remain disabled", mod.__doc__ or "")
            self.assertIn("Do not use visual generation for routine chat", mod.VISUAL_POLICY)


if __name__ == "__main__":
    unittest.main()
