from fastapi.testclient import TestClient

from hancock.api.app import create_app
from hancock.config import get_settings


def test_api_key_required(monkeypatch):
    monkeypatch.setenv("HANCOCK_API_KEY", "secret-test-key")
    get_settings.cache_clear()
    client = TestClient(create_app())
    r = client.post("/v1/ask", json={"question": "hi"})
    assert r.status_code == 401
    r2 = client.post(
        "/v1/ask",
        json={"question": "hi"},
        headers={"Authorization": "Bearer secret-test-key"},
    )
    assert r2.status_code != 401
    get_settings.cache_clear()
