import inspect

import image_response_compat as compat
import proactive_threads
import secure_desktop


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
    source = inspect.getsource(compat.install)
    assert "def cost_status(request: Request)" in source
    assert "def cost_status(username" not in source


def test_remaining_profile_desktop_routes_are_session_bound():
    source = inspect.getsource(secure_desktop.install)
    required_wrappers = {
        "secure_core_observe",
        "secure_hive_budget",
        "secure_core_research_status",
        "secure_message_quality",
        "secure_self_assessment",
        "secure_continuity_list",
        "secure_continuity_create",
        "secure_continuity_state",
        "secure_continuity_events",
    }
    for name in required_wrappers:
        assert f"def {name}" in source
    # The underlying legacy APIs may still accept username for compatibility,
    # but every exposed wrapper must derive it from the authenticated request.
    assert "continuity_list_impl(username=_profile(request)" in source
    assert "core_observe_impl(username=_profile(request)" in source
    assert "message_quality_impl(username=_profile(request))" in source
    assert "_profile(request)  # require a valid account" in source


def test_post_security_thread_routes_do_not_accept_username_selector():
    source = inspect.getsource(proactive_threads.install)
    assert "def message_thread(username" not in source
    assert "def message_thread_status(username" not in source
    assert "_profile_for_authorization(authorization)" in source
    auth_source = inspect.getsource(proactive_threads._profile_for_authorization)
    assert "auth.require_account(authorization)" in auth_source


def test_private_route_inventory_includes_profile_scoped_surfaces():
    expected = {
        "/desktop/core-observe",
        "/desktop/hive-budget",
        "/desktop/core-research-status",
        "/desktop/message-quality",
        "/desktop/self-assessment",
        "/desktop/continuity",
    }
    assert expected.issubset(secure_desktop.PRIVATE_PATHS)


def test_authoritative_app_chat_gate_preserves_authenticated_profile_boundary():
    # Read source text rather than importing janus_app: importing the authoritative
    # ASGI composition can start real runtime subsystems during a unit test.
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] / "janus_app.py").read_text(encoding="utf-8")
    assert "async def authoritative_chat(request: Request, payload: dict[str, Any])" in source
    assert "profile = secure_desktop._profile(request, payload)" in source
    assert 'safe["profile_id"] = profile' in source
    assert 'safe["username"] = profile' in source
    assert 'safe.pop("_janus_token", None)' in source
    assert "foreground_deliberate(profile, message)" in source
    assert "return await _call_chat_impl(previous, request, safe)" in source
    assert 'payload.get("profile_id") or payload.get("username")' not in source
