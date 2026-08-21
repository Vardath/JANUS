"""Local, network-free regression tests for JANUS password authentication.

Run with: python -m unittest tests.test_auth_local
"""
import importlib
import os
import tempfile
import unittest
from pathlib import Path


class AuthLocalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        os.environ["JANUS_AUTH_DB"] = str(Path(cls.tmp.name) / "auth-test.db")
        os.environ.pop("JANUS_SMTP_HOST", None)
        os.environ.pop("JANUS_SMTP_FROM", None)
        import auth
        cls.auth = importlib.reload(auth)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_register_login_me_and_duplicate(self):
        a = self.auth
        reg = a.register(a.RegisterRequest(username="tester", email="tester@example.com", password="Password1234"))
        self.assertTrue(reg["ok"])
        self.assertFalse(reg["email_delivery"])
        self.assertEqual(reg["account"]["username"], "tester")
        login = a.login(a.LoginRequest(identifier="tester", password="Password1234"))
        self.assertTrue(login["ok"])
        me = a.me("Bearer " + login["access_token"])
        self.assertEqual(me["account"]["email"], "tester@example.com")
        with self.assertRaises(a.HTTPException) as cm:
            a.register(a.RegisterRequest(username="tester", email="other@example.com", password="Password1234"))
        self.assertEqual(cm.exception.status_code, 409)

    def test_password_reset_invalidates_existing_sessions(self):
        a = self.auth
        reg = a.register(a.RegisterRequest(username="resetter", email="reset@example.com", password="Password1234"))
        old_token = reg["access_token"]
        with a._db() as c:
            reset_token = a._new_action_token(c, reg["account"]["id"], "reset_password", a.RESET_TTL)
        self.assertTrue(a.reset_password(a.ResetPasswordRequest(token=reset_token, new_password="NewPassword5678"))["ok"])
        self.assertIsNone(a.account_for_token(old_token))
        with self.assertRaises(a.HTTPException):
            a.login(a.LoginRequest(identifier="reset@example.com", password="Password1234"))
        self.assertTrue(a.login(a.LoginRequest(identifier="reset@example.com", password="NewPassword5678"))["ok"])

    def test_schema_has_required_columns(self):
        a = self.auth
        with a._db() as c:
            sessions = {r[1] for r in c.execute("PRAGMA table_info(sessions)")}
            tokens = {r[1] for r in c.execute("PRAGMA table_info(auth_tokens)")}
        self.assertTrue({"token_hash", "account_id", "created_at", "expires_at"}.issubset(sessions))
        self.assertTrue({"token_hash", "account_id", "purpose", "created_at", "expires_at", "used_at"}.issubset(tokens))


if __name__ == "__main__":
    unittest.main()
