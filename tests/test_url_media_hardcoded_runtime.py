from pathlib import Path


def test_runtime_hard_codes_url_media_ingestion_without_text_patch():
    app_module = Path('janus_app.py').read_text(encoding='utf-8')
    docker = Path('Dockerfile').read_text(encoding='utf-8')

    assert 'from url_media_ingest import install as install_url_media_ingest' in app_module
    assert 'install_url_media_ingest(app, curiosity_search_module)' in app_module
    assert 'janus_url_media_ingestion_hardcoded = True' in app_module

    assert 'uvicorn janus_app:app' in docker
    assert 'patch_url_media_ingestion.py' not in docker


def test_url_media_ingestion_wraps_the_same_foreground_function_used_by_chat():
    chat = Path('interface_chat.py').read_text(encoding='utf-8')
    ingest = Path('url_media_ingest.py').read_text(encoding='utf-8')

    assert 'curiosity_search.foreground_deliberate(profile,enriched)' in chat
    assert 'original=curiosity_module.foreground_deliberate' in ingest
    assert 'curiosity_module.foreground_deliberate=wrapped' in ingest
    assert "@app.get('/capabilities/research')" in ingest
