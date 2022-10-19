import requests

from patient_queue.utils import load_config_file


def test_pulsar_up(env_sample_file) -> None:
    """Checks whether the Pulsar service is up and running by attempting to access metrics. NOTE that docker
    infrastructure (or at least Pulsar) needs to be up and running for this test to work."""
    pulsar_port = load_config_file("PULSAR_HTTP_PORT", filename=env_sample_file).strip()
    res = requests.get(url=f"http://localhost:{pulsar_port}/metrics/")
    assert res.status_code == 200



