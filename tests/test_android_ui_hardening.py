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


def test_authoritative_build_orders_product_ui_before_runtime():
    text = Path('.github/workflows/build-android.yml').read_text(encoding='utf-8')
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


def test_android_phase3_version_is_not_stale_v069():
    text = Path('android/app/build.gradle').read_text(encoding='utf-8')
    assert "versionCode 70" in text
    assert "versionName '0.70'" in text
    assert 'v0.70: Phase 3 productization baseline' in text
