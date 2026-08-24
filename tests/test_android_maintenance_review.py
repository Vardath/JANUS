from pathlib import Path


def test_owner_maintenance_api_is_advisory_and_account_restricted():
    text = Path('maintenance_owner_api.py').read_text(encoding='utf-8')
    assert 'JANUS_MAINTENANCE_OWNER_PROFILE' in text
    assert '@router.get("/status")' in text
    assert '@router.post("/reviews/{review_id}/decision")' in text
    assert 'approved_for_manual_work' in text
    assert 'deferred' in text
    assert 'rejected' in text
    assert 'automatic_changes": False' in text
    assert 'maintenance_review.acknowledge' in text


def test_deployment_wires_owner_maintenance_api():
    docker = Path('Dockerfile').read_text(encoding='utf-8')
    patch = Path('tools/patch_maintenance_owner_api.py').read_text(encoding='utf-8')
    assert 'python tools/patch_maintenance_owner_api.py' in docker
    assert 'maintenance_owner_router' in patch
    assert 'app.include_router(maintenance_owner_router)' in patch
    assert 'maintenance_owner_status_route_present' in patch


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
