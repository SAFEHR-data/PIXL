from fastapi.testclient import TestClient

from hasher.main import app

client = TestClient(app)


def test_heart_beat_get():
    response = client.get("/heart-beat")
    assert response.status_code == 200
    assert response.json() == "OK"
