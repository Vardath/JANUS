"""Regression tests for profile-bound offline-chat idempotency receipts."""
import json
import sqlite3
import tempfile
import types
import unittest

from fastapi import HTTPException

from chat_receipt_security import install


class FakeInterfaceChat:
    pass


class ChatReceiptSecurityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        self.tmp.close()
        module = FakeInterfaceChat()

        def receipt_db():
            c = sqlite3.connect(self.tmp.name)
            c.row_factory = sqlite3.Row
            c.execute(
                """CREATE TABLE IF NOT EXISTS janus_chat_receipts(
                client_message_id TEXT PRIMARY KEY,
                profile_id TEXT NOT NULL,
                status TEXT NOT NULL,
                response_json TEXT,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
                )"""
            )
            return c

        module._receipt_db = receipt_db
        self.module = module
        install(module)

    def test_same_profile_can_replay_done_response(self):
        self.assertIsNone(self.module._claim_message("abc", "alice"))
        result = {"reply": "hello"}
        self.module._finish_message("abc", "alice", result)
        replay = self.module._claim_message("abc", "alice")
        self.assertEqual(replay, result)

    def test_other_profile_cannot_read_cached_response(self):
        self.assertIsNone(self.module._claim_message("shared-id", "alice"))
        self.module._finish_message("shared-id", "alice", {"reply": "alice secret"})
        with self.assertRaises(HTTPException) as cm:
            self.module._claim_message("shared-id", "bob")
        self.assertEqual(cm.exception.status_code, 409)

    def test_other_profile_cannot_overwrite_receipt(self):
        self.assertIsNone(self.module._claim_message("same", "alice"))
        self.module._finish_message("same", "alice", {"reply": "original"})
        self.module._finish_message("same", "bob", {"reply": "replacement"})
        replay = self.module._claim_message("same", "alice")
        self.assertEqual(replay["reply"], "original")


if __name__ == "__main__":
    unittest.main()
