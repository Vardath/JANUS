from pathlib import Path


def test_server_provenance_api_is_account_scoped_and_aggregates_existing_ledgers():
    text = Path('research_provenance_api.py').read_text(encoding='utf-8')
    assert 'auth.require_account' in text
    assert 'background_usefulness.audit' in text
    assert 'cost_governor.status' in text
    assert 'janus_curiosity_searches' in text
    assert 'sources' in text
    assert 'background_image_generation_enabled' in text


def test_android_provenance_ui_exposes_sources_suppression_and_costs():
    text = Path('tools/patch_android_research_provenance.py').read_text(encoding='utf-8')
    assert 'Background research' in text
    assert '/research-provenance/status' in text
    assert 'Recently suppressed before spending API budget' in text
    assert 'background_today_estimated_usd' in text
    assert 'Sources recorded' in text
    assert 'private chain-of-thought' in text


def test_android_build_applies_provenance_after_maintenance_before_runtime():
    text = Path('.github/workflows/build-android.yml').read_text(encoding='utf-8')
    maintenance = text.index('python tools/patch_android_maintenance_review.py')
    provenance = text.index('python tools/patch_android_research_provenance.py')
    runtime = text.index('python tools/patch_android_runtime_cores_v068.py')
    assert maintenance < provenance < runtime


def test_docker_deploys_provenance_route_patch():
    text = Path('Dockerfile').read_text(encoding='utf-8')
    assert 'python tools/patch_research_provenance_api.py' in text
