from fastapi.testclient import TestClient
from pixl_ehr.main import app, state, AppState

client = TestClient(app)


def test_heartbeat_response_is_200():
    response = client.get("/heart-beat")
    assert response.status_code == 200


def test_initial_state_has_no_token():
    assert not AppState().token_bucket.has_token


def test_updating_the_token_refresh_rate_to_negative_fails():

    response = client.post("/token-bucket-refresh-rate", json={"rate": -1})
    assert 400 <= response.status_code < 410


def test_updating_the_token_refresh_rate_updates_state():

    response = client.post("/token-bucket-refresh-rate", json={"rate": 1})
    assert state.token_bucket.has_token
    assert response.status_code == 200

    # This test uses shared global state, which must be reverted... not ideal.
    state.token_bucket = AppState().token_bucket
