from enum import Enum
from pathlib import Path


class VarNotFound(Exception):
    """ Customised exception for variable not found in .env file. """
    pass


class EnvFileNotFound(Exception):
    """ Customised exception for variable not found in .env file. """
    pass


class AvailableTopics(Enum):
    """
    In Pulsar, topics are offered to consumers for subscription. This Enum provides an overview over all the topics
    that are available as part of Pixl. At the moment, it is envisaged that there will be two different topics, one
    for the image and one for the EHR demographics download.
    """
    DICOM = "dicom"
    EHR = "ehr"


def load_config_file(env_var: str, filename=Path(__file__).parent.parent.parent.parent.joinpath(".env")) -> str:
    """ Reads relevant Pulsar configuration settings for Subscriber and Producer.

    As part of the configuration of the Pulsar Docker container, ports can be specified that are necessary for writing
    and receiving messages through Pulsar. This method retrieves information from the .env file wrt. which port has been
    configured for use.

    :returns: port information for PULSAR_BINARY_PROTOCOL env variable as configured in .env file
    """
    env_vars = {}

    if not Path(filename).exists():
        raise EnvFileNotFound(f"Specified environment file {filename} cannot be found.")

    with open(filename) as env_file:
        for line in env_file:
            name, var = line.partition("=")[::2]
            env_vars[name.strip()] = str(var).strip()

    if env_var not in env_vars:
        raise VarNotFound(f"{env_var} not contained in .env file.")

    return env_vars[env_var]
