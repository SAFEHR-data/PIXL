from enum import Enum


class AvailableChannels(Enum):
    """
    There will be two different subscription streams for both images and text data. This enum
    """
    IMAGES = "images"
    EHR = "ehr"


def load_config_file() -> str:
    """ Reads relevant Pulsar port for Subscriber and Producer.

    As part of the configuration of the Pulsar Docker container, ports can be specified that are necessary for writing
    and receiving messages through Pulsar. This method retrieves information from the .env file wrt. which port has been
    configured for use.

    :returns: port information for PULSAR_BINARY_PROTOCOL env variable as configured in .env file
    """
    env_vars = {}
    with open("namelist.txt") as myfile:
        for line in myfile:
            name, var = line.partition("=")[::2]
            env_vars[name.strip()] = str(var)

    if "PULSAR_BINARY_PROTOCOL" not in env_vars:
        raise Exception("Pulsar port information not contained in .env file.")

    return env_vars["PULSAR_BINARY_PROTOCOL"]
