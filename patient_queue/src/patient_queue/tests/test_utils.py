import pytest

from patient_queue.utils import load_config_file
from patient_queue.utils import EnvFileNotFound
from patient_queue.utils import VarNotFound


def test_load_config_file_var_present(env_sample_file) -> None:
    """Checks whether config file can be loaded and specified variable is present."""
    assert True, load_config_file("PULSAR_HTTP_PORT", filename=env_sample_file)


def test_load_config_file_var_not(env_sample_file):
    """Checks whether exception is raised if variable is not contained in environment file."""
    with pytest.raises(VarNotFound) as exc_info:
        load_config_file("TEST_ENV_VAR", filename=env_sample_file)
    assert exc_info.value.args[0] == 'TEST_ENV_VAR not contained in .env file.'