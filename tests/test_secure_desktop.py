"""Regression tests for session-bound desktop profile selection."""
import importlib
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


class FakeHeaders(dict):
    def get(self, key, default=None):
        return super().get(key.lower(), super().get(key, default))


class FakeRequest:
    def __init__(self, token="", query=None):
        self.headers = FakeHeaders({"authorization": f"Bearer {token}"} if token else {})
        self.query_params = query or {}


class SecureDesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        os.environ["JANUS_AUTH_DB"] = str(Path(cls.tmp.name) / "secure-test.db")
        import auth
        import secure_desktop
        cls.auth = importlib.reload(auth)
        cls.secure = importlib.reload(secure_desktop)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_authenticated_profile_overrides_spoofed_payload(self):
        a, s = self.auth, self.secure
        reg = a.register(a.RegisterRequest(username="alice", email="alice@example.com", password="Password1234"))
        request = FakeRequest(reg["access_token"])
        profile = s._profile(request, {"profile_id": "bob", "username": "bob", "_janus_token": "fake"})
        self.assertEqual(profile, "alice")

    def test_missing_or_invalid_session_is_rejected(self):
        s = self.secure
        with self.assertRaises(s.HTTPException) as cm:
            s._profile(FakeRequest(), {"profile_id": "victim"})
        self.assertEqual(cm.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()
