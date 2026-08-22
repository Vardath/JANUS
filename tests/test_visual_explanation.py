import asyncio
import importlib
import types


def test_assess_accepts_material_spatial_explanation():
    import visual_explanation as v
    decision = v.assess(
        "Can you explain how the 7 to 2 to 1 to 1 architecture connects?",
        "A" * 700 + " The specialists feed two hemispheres, then consensus and interface.",
        "Clear labelled diagram of the JANUS 7 specialist cores flowing into two hemispheres, then consensus, then interface",
    )
    assert decision["show"] is True
    assert decision["score"] >= 4


def test_assess_rejects_routine_diagnostic():
    import visual_explanation as v
    decision = v.assess(
        "Server status diagnostic please",
        "Everything is healthy. " * 80,
        "Diagram showing server heartbeat status and telemetry",
    )
    assert decision["show"] is False
    assert decision["reason"] == "routine_or_operational_topic"


def test_assess_rejects_decorative_nomination():
    import visual_explanation as v
    decision = v.assess("Tell me something interesting", "Brief answer", "A beautiful abstract glowing image")
    assert decision["show"] is False


def test_install_does_not_block_explicit_requests(monkeypatch):
    import visual_explanation as v
    calls = []

    async def original(profile, message, reply):
        calls.append((profile, message, reply))
        return "clean", {"generated": True}

    fake = types.SimpleNamespace(
        maybe_generate_for_chat=original,
        explicit_image_request=lambda message: True,
    )
    v.install(fake)
    clean, result = asyncio.run(fake.maybe_generate_for_chat("alice", "Generate an image", "reply"))
    assert clean == "clean"
    assert result["generated"] is True
    assert result["visual_decision"]["reason"] == "explicit_user_request"
    assert len(calls) == 1


def test_declined_auto_nomination_never_calls_renderer(monkeypatch):
    import visual_explanation as v
    generated = []

    async def original(profile, message, reply):
        raise AssertionError("original renderer path should not be called")

    async def generate(*args, **kwargs):
        generated.append((args, kwargs))
        return {"generated": True}

    fake = types.SimpleNamespace(
        maybe_generate_for_chat=original,
        explicit_image_request=lambda message: False,
        extract_visual_nomination=lambda reply: ("Short answer", "A decorative abstract image"),
        _account_by_profile=lambda profile: {"id": 1},
        generate_for_account=generate,
    )
    v.install(fake)
    clean, result = asyncio.run(fake.maybe_generate_for_chat("alice", "Tell me something interesting", "reply"))
    assert clean == "Short answer"
    assert result["generated"] is False
    assert result["reason"] == "visual nomination declined"
    assert generated == []
