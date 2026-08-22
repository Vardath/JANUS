from proactive_quality import assess, should_show_stored_message, similarity


def test_telemetry_chatter_is_rejected():
    text = (
        "I revisited two retained topics. Shared terms: integration, grounding; numeric check: none. "
        "Current functional signals: curiosity 0.82, tension 0.31, confidence 0.54. "
        "The cores completed 188 cycles and Consensus integrated the hemispheres."
    )
    result = assess(text)
    assert result["pass"] is False
    assert result["telemetry_heavy"] is True


def test_concrete_discovery_can_pass():
    text = (
        "I found a useful connection between the earlier error-correction discussion and distributed-system quorum design. "
        "Both separate local faults from system-level agreement, but the analogy breaks if independent failures become correlated. "
        "A worthwhile test would be to compare JANUS bridge failures against Byzantine quorum assumptions."
    )
    result = assess(text)
    assert result["pass"] is True, result
    assert result["score"] >= 0.5


def test_near_duplicate_is_suppressed():
    old = "I found a useful connection between memory retrieval and error correction; a test would compare failure recovery in both systems."
    new = "I found a useful connection between memory retrieval and error correction, and a test would compare failure recovery in both systems."
    result = assess(new, [old])
    assert similarity(old, new) > 0.7
    assert result["pass"] is False


def test_explicit_chat_messages_are_never_hidden_by_automatic_filter():
    noisy = "cycles 400, Fano d4, 1|3|4, consensus routing and runtime telemetry"
    assert should_show_stored_message(noisy, "chat") is True


def test_legacy_automatic_telemetry_is_hidden():
    noisy = "Pulse 22: cycles 400; Fano d4; 1|3|4; curiosity 0.82; tension 0.41; confidence 0.55."
    assert should_show_stored_message(noisy, "autonomous_hive") is False
