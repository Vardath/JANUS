import os

from server_v2 import maintenance_issue_mirror as mirror


def test_private_issue_mirror_is_disabled_without_explicit_opt_in(monkeypatch):
    monkeypatch.delenv("JANUS_MAINTENANCE_GITHUB_MIRROR", raising=False)
    monkeypatch.delenv("JANUS_MAINTENANCE_GITHUB_TOKEN", raising=False)
    state = mirror.status()
    assert state["enabled"] is False
    assert state["configured"] is False
    assert "no Contents/source-code write permission" in state["permission_intent"]


def test_comment_is_bounded_and_redacts_obvious_credentials():
    request = {
        "id": 7,
        "account_id": 1,
        "fingerprint": "abc123",
        "capability": "foreground_research",
        "severity": "normal",
        "state": "awaiting_supervisor_review",
        "occurrence_count": 3,
        "updated_at": 1234,
        "title": "Research capability failed",
        "detail": "Authorization: Bearer top-secret token=also-secret password=hunter2 web research unavailable",
    }
    text = mirror._comment(request)
    assert "top-secret" not in text
    assert "also-secret" not in text
    assert "hunter2" not in text
    assert "[REDACTED]" in text
    assert "Occurrences: `3`" in text
    assert "Render persistent store" in text


def test_mirror_request_does_not_touch_storage_when_disabled(monkeypatch):
    monkeypatch.setenv("JANUS_MAINTENANCE_GITHUB_MIRROR", "0")
    monkeypatch.setattr(mirror, "init_schema", lambda: (_ for _ in ()).throw(AssertionError("should not initialize")))
    result = mirror.mirror_request({"id": 1})
    assert result == {"mirrored": False, "reason": "disabled"}


def test_mirror_open_requests_noops_without_token(monkeypatch):
    monkeypatch.setenv("JANUS_MAINTENANCE_GITHUB_MIRROR", "1")
    monkeypatch.delenv("JANUS_MAINTENANCE_GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(mirror, "init_schema", lambda: (_ for _ in ()).throw(AssertionError("should not initialize")))
    assert mirror.mirror_open_requests() == {"mirrored": 0, "skipped": 0, "failed": 0}
