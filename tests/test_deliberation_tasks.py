"""Regression tests for persistent user-directed deliberation tasks."""
import importlib
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path


class DeliberationTaskTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db_path = str(Path(cls.tmp.name) / "deliberation.db")
        os.environ["JANUS_DB_PATH"] = cls.db_path
        import deliberation_tasks
        cls.d = importlib.reload(deliberation_tasks)
        # Initialize the production-owned deliberation schema before individual
        # tests clear table contents. This keeps the fixture aligned with the
        # real module instead of duplicating that schema here.
        cls.d._db().close()
        with sqlite3.connect(cls.db_path) as c:
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS desktop_memory(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    level TEXT NOT NULL DEFAULT 'trace',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS desktop_events(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        with sqlite3.connect(self.db_path) as c:
            c.execute("DELETE FROM desktop_memory")
            c.execute("DELETE FROM desktop_events")
            c.execute("DELETE FROM janus_deliberation_tasks")

    def _user_memory(self, text):
        with sqlite3.connect(self.db_path) as c:
            c.execute(
                "INSERT INTO desktop_memory(profile_id,role,content,level,created_at) VALUES('alice','user',?,'working','2026-08-21T00:00:00+00:00')",
                (text,),
            )

    def test_imperative_deliberation_phrases_are_detected(self):
        d = self.d
        for text in (
            "Mull it over.",
            "Keep thinking about that.",
            "Think it over.",
            "Ponder that for a while.",
            "Give it some thought.",
        ):
            self.assertTrue(d._is_deliberation_request(text), text)

    def test_ordinary_opinion_question_is_not_persistent_task(self):
        self.assertFalse(self.d._is_deliberation_request("What do you think about it?"))

    def test_generic_mull_it_over_retains_previous_user_topic(self):
        topic = "Could the apparent relation be caused by a shared symmetry rather than coincidence?"
        self._user_memory(topic)
        task = self.d.create_or_continue("alice", "Mull it over.")
        self.assertIsNotNone(task)
        self.assertEqual(task["topic"], topic)
        with sqlite3.connect(self.db_path) as c:
            c.row_factory = sqlite3.Row
            row = c.execute("SELECT * FROM janus_deliberation_tasks WHERE id=?", (task["id"],)).fetchone()
        self.assertEqual(row["status"], "active")
        self.assertEqual(row["pass_count"], 0)

    def test_same_topic_reaffirms_existing_task_instead_of_duplication(self):
        self._user_memory("Investigate the same unresolved mechanism.")
        first = self.d.create_or_continue("alice", "Mull it over.")
        second = self.d.create_or_continue("alice", "Keep thinking about that.")
        self.assertEqual(first["id"], second["id"])
        with sqlite3.connect(self.db_path) as c:
            count = c.execute("SELECT count(*) FROM janus_deliberation_tasks WHERE profile_id='alice'").fetchone()[0]
        self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
