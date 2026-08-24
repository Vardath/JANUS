from server_v2.senses import Appraisal, SenseFrame, merge_appraisals
from server_v2.topology import (
    CORE_NAMES,
    FANO_LINES,
    SPECIALIST_DIRECTIONS,
    SPECIALIST_ROLES,
    metadata,
    validate_fano_contract,
)


def test_original_seven_names_are_preserved_with_unique_fano_numbers():
    assert set(SPECIALIST_ROLES) == {
        "evidence", "logic", "counterpoint", "context", "memory", "safety", "novelty"
    }
    assert set(SPECIALIST_DIRECTIONS.values()) == set(range(1, 8))
    assert SPECIALIST_DIRECTIONS == {
        "evidence": 1,
        "safety": 2,
        "counterpoint": 3,
        "context": 4,
        "logic": 5,
        "novelty": 6,
        "memory": 7,
    }


def test_fano_lines_have_xor_closure_and_semantic_composites():
    validate_fano_contract()
    for a, b, c in FANO_LINES:
        assert a ^ b == c or a ^ c == b or b ^ c == a
    assert SPECIALIST_ROLES["counterpoint"].axes == ("E", "V")
    assert SPECIALIST_ROLES["logic"].axes == ("E", "P")
    assert SPECIALIST_ROLES["novelty"].axes == ("V", "P")
    assert SPECIALIST_ROLES["memory"].axes == ("E", "V", "P")


def test_both_hemispheres_receive_all_seven_by_contract():
    left = metadata("left_hemisphere")
    right = metadata("right_hemisphere")
    assert "all seven" in left["purpose"]
    assert "all seven" in right["purpose"]
    assert "logic" in left["meaning"]
    assert "imagination" in right["meaning"]


def test_front_and_interface_are_distinct_affective_action_layers():
    assert len(CORE_NAMES) == 11
    front = metadata("front")
    interface = metadata("interface")
    assert front["layer"] == "intermediary"
    assert "affective appraisal" in front["meaning"]
    assert interface["layer"] == "interface"
    assert "action" in interface["meaning"]
    assert "new sensing" in interface["semantics"]


def test_sense_frames_are_multimodal_and_bounded():
    frame = SenseFrame("image", "camera", "visual scene", salience=2.0, uncertainty=-1.0, novelty=0.8)
    assert frame.salience == 1.0
    assert frame.uncertainty == 0.0
    assert frame.novelty == 0.8


def test_affective_merge_preserves_high_risk_and_uncertainty():
    left = Appraisal(confidence=0.8, valence=-0.2, risk=0.3, uncertainty=0.2)
    right = Appraisal(confidence=0.4, valence=0.4, risk=0.9, uncertainty=0.8, urgency=0.7)
    merged = merge_appraisals(left, right)
    assert merged.confidence == 0.6
    assert merged.risk == 0.9
    assert merged.uncertainty == 0.8
    assert merged.action_posture() == "interrupt_or_warn"
