from pathlib import Path


def test_artifact_patch_exposes_android_artifact_workflow():
    text = Path('tools/patch_android_artifacts.py').read_text(encoding='utf-8')
    # The patch source contains escaped single quotes because the HTML button
    # fragment is itself a Python single-quoted string. Test the semantic
    # markers independently instead of requiring the generated HTML spelling.
    assert "refreshArtifacts()" in text
    assert "artifacts" in text
    assert "createArtifact('continuity_report')" in text
    assert "createArtifact('research_digest')" in text
    assert "api('GET','/artifacts')" in text
    assert "api('GET','/artifacts/'+encodeURIComponent(id))" in text
    assert "pendingAttachments.push" in text
    assert "Use in Chat" in text


def test_android_build_applies_artifact_patch_after_attachments_before_runtime():
    text = Path('.github/workflows/build-android.yml').read_text(encoding='utf-8')
    attach = text.index('python tools/patch_android_file_attachments.py')
    artifact = text.index('python tools/patch_android_artifacts.py')
    runtime = text.index('python tools/patch_android_runtime_cores_v068.py')
    assert attach < artifact < runtime


def test_server_artifact_routes_remain_account_bound():
    text = Path('outbound_artifacts.py').read_text(encoding='utf-8')
    assert '@router.get("")' in text
    assert '@router.get("/{artifact_id}")' in text
    assert '@router.post("")' in text
    assert 'WHERE a.account_id=?' in text
    assert 'WHERE a.id=? AND a.account_id=?' in text
    assert 'attachment_api.store_generated_file' in text
