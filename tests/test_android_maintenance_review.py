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


def test_android_maintenance_ui_has_explicit_manual_only_decisions():
    text = Path('tools/patch_android_maintenance_review.py').read_text(encoding='utf-8')
    assert 'Maintenance review' in text
    assert '/maintenance/status' in text
    assert '/maintenance/reviews/' in text
    assert 'Approve for manual work' in text
    assert 'approved_for_manual_work' in text
    assert 'deferred' in text
    assert 'rejected' in text
    assert 'will not make or deploy any changes automatically' in text
    assert 'cannot change code, dependencies, models, configuration or deployments by itself' in text


def test_phase3_composer_patch_order_preserves_existing_product_features():
    workflow = Path('.github/workflows/build-android.yml').read_text(encoding='utf-8')
    assert 'python tools/compose_android_phase3.py' in workflow
    text = Path('tools/compose_android_phase3.py').read_text(encoding='utf-8')
    attach = text.index('tools/patch_android_file_attachments.py')
    artifacts = text.index('tools/patch_android_artifacts.py')
    research = text.index('tools/patch_android_research_workspace.py')
    maintenance = text.index('tools/patch_android_maintenance_review.py')
    runtime = text.index('tools/patch_android_runtime_cores_v068.py')
    assert attach < artifacts < research < maintenance < runtime
