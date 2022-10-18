from enum import Enum
from pathlib import Path


class VarNotFound(Exception):
    """ Customised exception for variable not found in .env file. """
    pass


class AvailableChannels(Enum):
    """
    There will be two different subscription streams for both images and text data. This enum
    """
    IMAGES = "images"
    EHR = "ehr"


def load_config_file(env_var: str, filename=Path(__file__).parent.parent.parent.parent.joinpath(".env")) -> str:
    """ Reads relevant Pulsar port for Subscriber and Producer.

    As part of the configuration of the Pulsar Docker container, ports can be specified that are necessary for writing
    and receiving messages through Pulsar. This method retrieves information from the .env file wrt. which port has been
    configured for use.

    :returns: port information for PULSAR_BINARY_PROTOCOL env variable as configured in .env file
    """
    env_vars = {}
    with open(filename) as env_file:
        for line in env_file:
            name, var = line.partition("=")[::2]
            env_vars[name.strip()] = str(var)

    if env_var not in env_vars:
        raise VarNotFound(f"{env_var} not contained in .env file.")

    return env_vars[env_var]
