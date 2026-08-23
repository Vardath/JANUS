from pathlib import Path


def test_research_patch_exposes_workspace_categories_and_chat_handoff():
    text = Path('tools/patch_android_research_workspace.py').read_text(encoding='utf-8')
    assert 'refreshResearchWorkspace()' in text
    assert "api('GET','/research/workspace')" in text
    assert "api('POST','/research/workspace/seed',{})" in text
    assert "setResearchFilter('established')" in text
    assert "setResearchFilter('hypotheses')" in text
    assert "setResearchFilter('negative')" in text
    assert "setResearchFilter('open')" in text
    assert "setResearchFilter('tests')" in text
    assert 'Retained negative result' in text
    assert 'Discuss in Chat' in text
    assert 'Preserve its current epistemic status' in text


def test_android_build_applies_research_patch_after_artifacts_before_runtime():
    text = Path('.github/workflows/build-android.yml').read_text(encoding='utf-8')
    attach = text.index('python tools/patch_android_file_attachments.py')
    artifact = text.index('python tools/patch_android_artifacts.py')
    research = text.index('python tools/patch_android_research_workspace.py')
    runtime = text.index('python tools/patch_android_runtime_cores_v068.py')
    assert attach < artifact < research < runtime


def test_server_research_workspace_preserves_epistemic_boundaries():
    text = Path('research_workspace.py').read_text(encoding='utf-8')
    assert '@router.get("/workspace")' in text
    assert '@router.post("/workspace/seed")' in text
    assert 'negative_result' in text
    assert 'closed_negative' in text
    assert 'Do not present hypotheses/interpretations as established physics' in text
    assert 'WHERE profile_id=? AND id=?' in text
