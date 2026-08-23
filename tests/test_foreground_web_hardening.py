from pathlib import Path


def test_foreground_web_bridge_has_youtube_hardening():
    text = Path("foreground_web_bridge.py").read_text(encoding="utf-8")
    assert "direct_youtube_sources" in text
    assert "at most 8 relevant videos" in text
    assert "captions/transcript" in text
    assert "label them as indirect" in text
    assert "hemispheres -> consensus -> interface" in text


def test_context_followups_do_not_force_research():
    text = Path("foreground_web_bridge.py").read_text(encoding="utf-8")
    assert "_context_only_followup" in text
    assert "those are to go along with" in text
    assert "return original(profile, message)" in text
