from fastapi import FastAPI
from fastapi.testclient import TestClient

from protocol_capabilities import router


def make_app():
    app = FastAPI()

    @app.post('/auth/register')
    def register():
        return {}

    @app.post('/auth/login')
    def login():
        return {}

    @app.post('/files/upload')
    def upload():
        return {}

    @app.get('/research/workspace')
    def research():
        return {}

    @app.get('/maintenance/status')
    def maintenance():
        return {}

    @app.post('/maintenance/reviews/{review_id}/decision')
    def decision(review_id: int):
        return {'id': review_id}

    @app.get('/research-provenance/status')
    def provenance():
        return {}

    @app.post('/images/generate')
    def image():
        return {}

    app.include_router(router)
    return app


def test_public_capability_snapshot_is_truthful_and_safe():
    response = TestClient(make_app()).get('/protocol/capabilities')
    assert response.status_code == 200
    data = response.json()
    assert data['protocol_version'] == 1
    assert data['features']['protocol_negotiation'] is True
    assert data['features']['auth_password'] is True
    assert data['features']['research_workspace'] is True
    assert data['features']['maintenance_review'] is True
    assert data['features']['research_provenance'] is True
    assert data['features']['background_multi_core_images'] is False
    assert data['safety_boundaries']['whole_state_overwrite'] is False
    assert data['safety_boundaries']['autonomous_code_changes'] is False
    text = response.text.lower()
    assert 'token' not in text
    assert 'password_hash' not in text


def test_missing_optional_routes_are_reported_unavailable_not_invented():
    app = FastAPI()
    app.include_router(router)
    data = TestClient(app).get('/protocol/capabilities').json()
    assert data['features']['attachments'] is False
    assert data['features']['maintenance_review'] is False
    assert data['features']['research_provenance'] is False
