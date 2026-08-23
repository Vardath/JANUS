from pathlib import Path


def test_theme_patch_exposes_persistent_accessible_controls():
    text = Path('tools/patch_android_ui_hardening.py').read_text(encoding='utf-8')
    for marker in [
        'Interface theme', 'themeMode', 'themeAccent', 'themeUser', 'themeSurface',
        'saveThemeSettings()', 'resetThemeSettings()', 'prefers-color-scheme',
        '--janus-accent-text', 'contrastText', 'localStorage.janusThemeMode',
    ]:
        assert marker in text


def test_theme_patch_keeps_settings_device_local():
    text = Path('tools/patch_android_ui_hardening.py').read_text(encoding='utf-8')
    assert 'Theme choices do not change JANUS cognition or server state.' in text
    assert "api('POST'" not in text
    assert "api('PUT'" not in text


def test_native_artifact_export_patch_uses_account_authenticated_downloads():
    text = Path('tools/patch_android_artifact_export.py').read_text(encoding='utf-8')
    for marker in [
        'ACTION_CREATE_DOCUMENT', 'ACTION_SEND', 'FLAG_GRANT_READ_URI_PERMISSION',
        'FileProvider.getUriForFile', '/files/', '/download', 'Authorization',
        'exportArtifactNative', 'shareArtifactNative', 'Download / Export', 'Share',
    ]:
        assert marker in text
    assert 'shared_artifacts' in text
    assert 'file_paths.xml' in text


def test_authoritative_build_uses_hard_coded_android_product():
    workflow = Path('.github/workflows/build-android.yml').read_text(encoding='utf-8')
    assert 'python tools/compose_android_phase3.py' not in workflow
    assert 'Persist composed Android product into source' not in workflow
    assert 'Validate hard-coded Android UI JavaScript' in workflow
    assert 'Verify hard-coded Android product markers' in workflow


def test_phase3_composer_is_retained_as_legacy_migration_tool_only():
    text = Path('tools/compose_android_phase3.py').read_text(encoding='utf-8')
    names = [
        'patch_android_file_attachments.py',
        'patch_android_artifacts.py',
        'patch_android_artifact_export.py',
        'patch_android_research_workspace.py',
        'patch_android_maintenance_review.py',
        'patch_android_research_provenance.py',
        'patch_android_protocol_capabilities.py',
        'patch_android_ui_hardening.py',
        'patch_android_runtime_cores_v068.py',
    ]
    positions = [text.index(name) for name in names]
    assert positions == sorted(positions)
    for marker in ['Android Phase 3 composition verified', 'Download / Export', 'Compatibility', 'themeMode']:
        assert marker in text


def test_android_phase3_version_is_v071_hard_coded_product():
    text = Path('android/app/build.gradle').read_text(encoding='utf-8')
    assert "versionCode 71" in text
    assert "versionName '0.71'" in text
    assert 'v0.71: hard-coded Phase 3 product build' in text


def test_fast_offline_chat_retry_is_complete_and_not_half_committed():
    queue = Path('android/app/src/main/java/com/vardath/janus/JanusOfflineQueue.java').read_text(encoding='utf-8')
    worker_path = Path('android/app/src/main/java/com/vardath/janus/JanusQueueRetryWorker.java')
    assert worker_path.exists(), 'JanusOfflineQueue schedules JanusQueueRetryWorker, so the worker must exist in the same commit.'
    worker = worker_path.read_text(encoding='utf-8')
    for marker in ['scheduleFastRetries', '8L, 25L, 60L', 'JanusQueueRetryWorker.class']:
        assert marker in queue
    for marker in ['class JanusQueueRetryWorker', 'JanusOfflineQueue.flush', 'pendingCount']:
        assert marker in worker
