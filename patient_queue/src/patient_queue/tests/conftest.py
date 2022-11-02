import pytest
import pulsar

from patient_queue.utils import load_config_file

@pytest.fixture(scope="session")
def env_sample_file():
    """generates EHR demographics file that is needed for renaming"""
    sample_file = "./.env.txt"
    sample_entries = {"PULSAR_HTTP_PORT": 7071, "PULSAR_BINARY_PROTOCOL": 7072}
    with open(sample_file, 'w') as sfile:
        for k, v in sample_entries.items():
            sfile.write(f"{k} = {v}\n")
    return sample_file


@pytest.fixture(scope="session")
def produce_sample_msg():
    """Generates sample message on queue for consumer tests."""
    pulsar_binary_port = load_config_file(env_var="PULSAR_BINARY_PROTOCOL")
    client = pulsar.Client(f"pulsar://localhost:{pulsar_binary_port}")
    producer = client.create_producer("/".join(["public", "default", "test"]), block_if_queue_full=True)
    producer.send("test".encode('utf-8'))
