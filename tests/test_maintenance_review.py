import importlib
import sqlite3


def _module(tmp_path, monkeypatch):
    monkeypatch.setenv("JANUS_DB_PATH", str(tmp_path / "maintenance.sqlite3"))
    monkeypatch.setenv("JANUS_MAINTENANCE_OWNER_PROFILE", "owner-test")
    monkeypatch.delenv("JANUS_MAINTENANCE_OWNER_EMAIL", raising=False)
    import maintenance_review
    return importlib.reload(maintenance_review)


def test_report_is_advisory_and_requires_owner_review(tmp_path, monkeypatch):
    m = _module(tmp_path, monkeypatch)
    report = m.build_report(None, "test")
    assert report["advisory_only"] is True
    assert report["owner_approval_required"] is True
    assert report["chatgpt_review_requested"] is True
    assert report["automatic_code_changes_allowed"] is False
    assert report["automatic_dependency_upgrades_allowed"] is False
    assert report["automatic_model_switches_allowed"] is False
    assert report["automatic_deployment_allowed"] is False
    assert report["external_model_api_calls_used"] == 0
    assert {x["area"] for x in report["review_sections"]} >= {"security", "runtime", "models_and_apis", "architecture", "tests"}


def test_run_review_persists_email_draft_and_owner_message(tmp_path, monkeypatch):
    m = _module(tmp_path, monkeypatch)
    m._init_db()
    with sqlite3.connect(m.DB_PATH) as c:
        c.execute("CREATE TABLE IF NOT EXISTS desktop_events(id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id TEXT, event_type TEXT, detail TEXT, created_at TEXT)")
    monkeypatch.setattr(m, "_smtp_send", lambda subject, body: (False, "smtp intentionally absent"))
    result = m.run_review(None, "test-manual")
    assert result["requires_owner_approval"] is True
    assert result["automatic_changes"] is False
    assert result["notification_sent"] is False
    assert "approval required" in result["email_subject"].lower()
    assert "No code, dependency, model, API, configuration, or deployment change has been made automatically." in result["email_body"]
    assert result["owner_message_created"] is True

    with sqlite3.connect(m.DB_PATH) as c:
        c.row_factory = sqlite3.Row
        row = c.execute("SELECT * FROM janus_maintenance_review WHERE id=?", (result["review_id"],)).fetchone()
        msg = c.execute("SELECT * FROM desktop_events WHERE profile_id='owner-test' AND event_type='proactive_message'").fetchone()
    assert row["review_state"] == "awaiting_owner_review"
    assert row["email_subject"] == result["email_subject"]
    assert row["email_body"] == result["email_body"]
    assert row["owner_message_created"] == 1
    assert msg is not None


def test_acknowledge_records_disposition_but_never_executes_upgrade(tmp_path, monkeypatch):
    m = _module(tmp_path, monkeypatch)
    monkeypatch.setattr(m, "_smtp_send", lambda subject, body: (False, "disabled"))
    result = m.run_review(None, "test")
    ack = m.acknowledge(result["review_id"], "approved_for_manual_work")
    assert ack["review_state"] == "approved_for_manual_work"
    assert ack["automatic_changes"] is False
    status = m.status()
    assert status["owner_approval_required"] is True
    assert status["automatic_changes"] is False
