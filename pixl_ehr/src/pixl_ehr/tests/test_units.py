"""
This file contains unit tests that do not require any test services
"""
from fastapi.testclient import TestClient
from pixl_ehr.main import AppState, app, state
from requests import Response

client = TestClient(app)


def _is_error(response: Response) -> bool:
    return 400 <= response.status_code < 450


def test_heartbeat_response_is_200() -> None:
    response = client.get("/heart-beat")
    assert response.status_code == 200


def test_initial_state_has_no_token() -> None:
    assert not AppState().token_bucket.has_token


def test_updating_the_token_refresh_rate_to_negative_fails() -> None:

    response = client.post("/token-bucket-refresh-rate", json={"rate": -1})
    assert _is_error(response)


def test_updating_the_token_refresh_rate_to_string_fails() -> None:

    response = client.post("/token-bucket-refresh-rate", json={"rate": "a string"})
    assert _is_error(response)


def test_updating_the_token_refresh_rate_updates_state() -> None:

    response = client.post("/token-bucket-refresh-rate", json={"rate": 1})
    assert state.token_bucket.has_token
    assert response.status_code == 200

    # This test uses shared global state, which must be reverted... not ideal.
    state.token_bucket = AppState().token_bucket
