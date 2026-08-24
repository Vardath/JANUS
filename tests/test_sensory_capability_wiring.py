from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_non_model_sensory_bus_routes_full_137_society():
    text = read("server_v2/sensory_bus.py")
    assert "for name in SPECIALISTS" in text
    assert '"left_hemisphere"' in text
    assert '"right_hemisphere"' in text
    assert "FRONT_CORE" in text
    assert "INTERFACE_CORE" in text
    assert '"model_calls": 0' in text
    assert "mind._model_reply" not in text
    assert "web_research(" not in text


def test_chat_capabilities_are_typed_senses_not_direct_front_injection():
    text = read("server_v2/chat.py")
    for modality in ('"file"', '"image"', '"audio"', '"web"', '"memory"'):
        assert f"sensory_bus.ingest(" in text
        assert modality in text
    assert "mind._front(" not in text
    assert "mind._record_core" not in text
    assert "visual_memory" in text
    assert "youtube_transcript" in text


def test_generated_images_reenter_as_image_sense():
    text = read("server_v2/images.py")
    assert "sensory_bus.ingest(" in text
    assert '"image"' in text
    assert '"generated_visual"' in text
    assert "background_multi_core_image_generation" in text


def test_sensory_bus_preserves_existing_architecture_boundary():
    mind = read("server_v2/mind.py")
    assert "Every sensed event is projected through all seven original subconscious cores" in mind
    assert "Interface output is never recursively injected straight back into Front" in mind
    assert "background_external_api_calls = 0" in mind
