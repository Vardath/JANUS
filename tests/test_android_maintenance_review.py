from pathlib import Path


def test_clean_server_owner_maintenance_is_advisory_and_account_restricted():
    text = Path('server_v2/maintenance.py').read_text(encoding='utf-8')
    assert 'JANUS_MAINTENANCE_OWNER_PROFILE' in text
    assert '@router.get("/maintenance/status")' in text
    assert '@router.post("/maintenance/reviews/{review_id}/decision")' in text
    assert 'approved_for_manual_work' in text
    assert 'deferred' in text
    assert 'rejected' in text
    assert 'automatic_changes":False' in text or '"automatic_changes":False' in text
    assert 'automatic_deploy":False' in text or '"automatic_deploy":False' in text
    assert 'Maintenance decisions are restricted to the JANUS owner account' in text


def test_deployment_wires_clean_owner_maintenance_router_without_legacy_patch_chain():
    docker = Path('Dockerfile').read_text(encoding='utf-8')
    render = Path('render.yaml').read_text(encoding='utf-8')
    entry = Path('server_v2/entrypoint.py').read_text(encoding='utf-8')
    maintenance = Path('server_v2/maintenance.py').read_text(encoding='utf-8')
    assert 'uvicorn server_v2.entrypoint:app' in docker
    assert 'uvicorn server_v2.entrypoint:app' in render
    assert 'maintenance_router' in entry
    assert 'app.include_router(maintenance_router)' in entry
    assert '("/maintenance/status","GET")' in entry
    assert '("/maintenance/reviews/{review_id}/decision","POST")' in entry
    assert '@router.get("/maintenance/status")' in maintenance
    assert '@router.post("/maintenance/reviews/{review_id}/decision")' in maintenance
    assert 'patch_maintenance_owner_api.py' not in docker


def test_native_android_maintenance_ui_has_manual_only_decisions():
    text = Path('android/app/src/main/java/com/vardath/janus/MainActivity.java').read_text(encoding='utf-8')
    assert 'Maintenance Review' in text
    assert '/maintenance/status' in text
    assert '/maintenance/reviews/' in text
    assert 'Button approve=button("Approve")' in text
    assert 'approved_for_manual_work' in text
    assert 'deferred' in text
    assert 'rejected' in text
    assert 'No automatic changes will be made.' in text
    assert 'It never authorizes JANUS to edit code, install packages, change models/APIs or deploy itself.' in text


def test_authoritative_android_workflow_does_not_recompose_legacy_product():
    workflow = Path('.github/workflows/build-android.yml').read_text(encoding='utf-8')
    assert 'python tools/compose_android_phase3.py' not in workflow
    assert 'python tools/patch_android_' not in workflow
    assert 'Compile authoritative Java client' in workflow
    assert 'Build debug APK' in workflow
