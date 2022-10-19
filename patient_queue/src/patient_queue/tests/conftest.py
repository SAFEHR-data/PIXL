import pytest


@pytest.fixture(scope="session")
def env_sample_file():
    """generates EHR demographics file that is needed for renaming"""
    sample_file = "./.env.txt"
    sample_entries = {"PULSAR_HTTP_PORT": 8080, "PULSAR_HTTP_PORT": 8081}
    with open(sample_file, 'w') as sfile:
        for k, v in sample_entries.items():
            sfile.write(f"{k} = {v}\n")
    return sample_file

