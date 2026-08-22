import types

import image_response_compat as compat


class DummyRequest:
    headers = {}
    query_params = {}


def test_authenticated_payload_overrides_forged_profile(monkeypatch):
    request = DummyRequest()
    monkeypatch.setattr(compat.secure_desktop, "_profile", lambda req, payload=None: "alice")
    payload = {
        "profile_id": "bob",
        "username": "bob",
        "message": "hello",
        "client_message_id": "m1",
    }
    profile, safe = compat._authenticated_payload(request, payload)
    assert profile == "alice"
    assert safe["profile_id"] == "alice"
    assert safe["username"] == "alice"
    assert safe["message"] == "hello"
    assert payload["profile_id"] == "bob"  # input is copied, not mutated


def test_authenticated_payload_uses_server_identity_before_side_effects(monkeypatch):
    calls = []
    request = DummyRequest()

    def resolve(req, payload=None):
        calls.append((req, dict(payload or {})))
        return "owner"

    monkeypatch.setattr(compat.secure_desktop, "_profile", resolve)
    profile, safe = compat._authenticated_payload(
        request,
        {"profile_id": "victim", "username": "victim", "text": "status"},
    )
    assert calls and calls[0][1]["profile_id"] == "victim"
    assert profile == "owner"
    assert safe["profile_id"] == "owner"
    assert safe["username"] == "owner"


def test_cost_status_no_longer_accepts_client_username():
    # Contract guard: the live route obtains identity from Request/authentication,
    # not from a username query argument. This prevents cross-profile cost reads.
    import inspect
    source = inspect.getsource(compat.install)
    assert "def cost_status(request: Request)" in source
    assert "def cost_status(username" not in source
