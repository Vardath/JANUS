from pathlib import Path


def test_self_diagnosis_schema_and_handoff_are_governed():
    d = Path('server_v2/diagnostics.py').read_text(encoding='utf-8')
    assert 'v2_capability_requests' in d
    assert 'v2_chat_history_full' in d
    assert 'awaiting_supervisor_review' in d
    assert 'JANUS -> CHATGPT SUPERVISOR HANDOFF' in d
    assert 'Review the private GitHub repository Vardath/JANUS thoroughly' in d
    assert 'automatic_chatgpt_injection' in d
    assert 'copy_or_share_under_owner_control' in d
    assert 'JANUS itself did not make or execute this decision' in d
    assert 'apply_supervisor_decisions' in d


def test_chat_records_visible_history_and_failure_requests():
    chat = Path('server_v2/chat.py').read_text(encoding='utf-8')
    assert 'user_visible_message' in chat
    assert 'diagnostics.record_chat_turn' in chat
    assert 'diagnostics.inspect_chat' in chat
    assert 'supervisor_review_queued' in chat


def test_maintenance_exposes_owner_handoff_without_self_modification():
    m = Path('server_v2/maintenance.py').read_text(encoding='utf-8')
    assert '@router.get("/maintenance/supervisor-handoff")' in m
    assert '@router.post("/maintenance/diagnostics/report")' in m
    assert 'automatic_chatgpt_injection' in m
    assert 'automatic_changes":False' in m
    assert 'automatic_deploy":False' in m


def test_repo_decision_ledger_is_supervisor_owned():
    text = Path('server_v2/supervisor_decisions.json').read_text(encoding='utf-8')
    assert 'ChatGPT Supervisor updates this file' in text
    assert 'JANUS never writes or self-approves this file' in text


def test_protocol_advertises_boundary():
    p = Path('server_v2/protocol.py').read_text(encoding='utf-8')
    for marker in ['self_diagnosis', 'capability_request_ledger', 'chatgpt_supervisor_handoff', 'supervisor_decision_sync']:
        assert marker in p
    for marker in ['janus_can_self_modify', 'janus_can_self_approve_maintenance', 'janus_can_self_deploy', 'automatic_chatgpt_injection']:
        assert marker in p
