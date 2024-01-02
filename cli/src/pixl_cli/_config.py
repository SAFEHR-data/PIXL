"""Configuration of CLI from config file."""
from pathlib import Path

import yaml


def _load_config(filename: str = "pixl_config.yml") -> dict:
    """CLI configuration generated from a .yaml file"""
    if not Path(filename).exists():
        msg = f"Failed to find {filename}. It must be present " f"in the current working directory"
        raise OSError(msg)

    with Path(filename).open() as config_file:
        config_dict = yaml.safe_load(config_file)
    return dict(config_dict)


cli_config = _load_config()
