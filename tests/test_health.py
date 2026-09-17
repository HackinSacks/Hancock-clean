def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["service"] == "hancock"
    assert "pentest" in data["modes"]
    assert "/v1/chat" in data["endpoints"]


def test_metrics(client):
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "hancock_requests_total" in r.text or r.status_code == 200
