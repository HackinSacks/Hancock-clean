import pytest
from fastapi.testclient import TestClient

from hancock.api.app import create_app


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("HANCOCK_API_KEY", "")
    from hancock.config import get_settings

    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as c:
        yield c
    get_settings.cache_clear()
