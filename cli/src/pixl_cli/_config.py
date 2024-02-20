#  Copyright (c) University College London Hospitals NHS Foundation Trust
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""Configuration of CLI from config file."""
from pathlib import Path
from typing import Optional

import yaml
from decouple import config

API_SETTINGS = {"ehr_api": {}, "imaging_api": {}}  # type: dict
API_SETTINGS["ehr_api"]["host"] = config("PIXL_EHR_API_HOST", default="localhost")
API_SETTINGS["ehr_api"]["port"] = int(config("PIXL_EHR_API_PORT", default=7006))
API_SETTINGS["ehr_api"]["default_rate"] = int(config("PIXL_EHR_API_RATE", default=1))
API_SETTINGS["imaging_api"]["host"] = config("PIXL_IMAGING_API_HOST", default="localhost")
API_SETTINGS["imaging_api"]["port"] = int(config("PIXL_IMAGING_API_PORT", default=7007))
API_SETTINGS["imaging_api"]["default_rate"] = int(config("PIXL_IMAGING_API_RATE", default=1))


class APIConfig:
    """API Configuration"""

    def __init__(self, kwargs: dict) -> None:
        """Initialise the APIConfig class"""
        self.host: Optional[str] = None
        self.port: Optional[int] = None
        self.default_rate: Optional[int] = None

        self.__dict__.update(kwargs)

    @property
    def base_url(self) -> str:
        """Return the base url for the API"""
        return f"http://{self.host}:{self.port}"


def api_config_for_queue(queue_name: str) -> APIConfig:
    """Configuration for an API associated with a queue"""
    config_key = f"{queue_name}_api"

    if config_key not in API_SETTINGS:
        msg = (
            f"Cannot update the rate for {queue_name}. {config_key} was"
            f" not specified in the configuration"
        )
        raise ValueError(msg)

    return APIConfig(API_SETTINGS[config_key])


def _load_config(filename: str = "pixl_config.yml") -> dict:
    """CLI configuration generated from a .yaml file"""
    if not Path(filename).exists():
        msg = f"Failed to find {filename}. It must be present in the current working directory"
        raise FileNotFoundError(msg)

    with Path(filename).open() as config_file:
        config_dict = yaml.safe_load(config_file)
    return dict(config_dict)


cli_config = _load_config()
