def test_homepage_returns_success(client):
    response = client.get("/")
    assert response.status_code == 200


def test_health_endpoint_returns_success(client):
    response = client.get("/health")
    assert response.status_code == 200
