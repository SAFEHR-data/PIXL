from patient_queue.utils import load_config_file


def test_load_config_file() -> None:
    """ Check whether config file can be loaded """
    config = load_config_file("PULSAR_HTTP_PORT")
