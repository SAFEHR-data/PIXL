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
from typing import Optional

from decouple import config

API_SETTINGS = {"ehr_api": {}, "imaging_api": {}}  # type: dict
API_SETTINGS["ehr_api"]["host"] = config("PIXL_EHR_API_HOST", default="localhost")
API_SETTINGS["ehr_api"]["port"] = int(config("PIXL_EHR_API_PORT", default=7006))
API_SETTINGS["ehr_api"]["default_rate"] = int(config("PIXL_EHR_API_RATE", default=1))
API_SETTINGS["imaging_api"]["host"] = config("PIXL_IMAGING_API_HOST", default="localhost")
API_SETTINGS["imaging_api"]["port"] = int(config("PIXL_IMAGING_API_PORT", default=7007))
API_SETTINGS["imaging_api"]["default_rate"] = int(config("PIXL_IMAGING_API_RATE", default=1))

SERVICE_SETTINGS = {"rabbitmq": {}, "postgres": {}}  # type: dict
SERVICE_SETTINGS["rabbitmq"]["host"] = config("RABBITMQ_HOST", default="localhost")
SERVICE_SETTINGS["rabbitmq"]["port"] = int(config("RABBITMQ_PORT", default=7008))
SERVICE_SETTINGS["rabbitmq"]["username"] = config("RABBITMQ_USERNAME", default="rabbitmq_username")
SERVICE_SETTINGS["rabbitmq"]["password"] = config("RABBITMQ_PASSWORD", default="rabbitmq_password")

SERVICE_SETTINGS["postgres"]["host"] = config("POSTGRES_HOST", default="localhost")
SERVICE_SETTINGS["postgres"]["port"] = int(config("POSTGRES_PORT", default=7001))
SERVICE_SETTINGS["postgres"]["username"] = config("PIXL_DB_USER", default="pixl_db_username")
SERVICE_SETTINGS["postgres"]["password"] = config("PIXL_DB_PASSWORD", default="pixl_db_password")
SERVICE_SETTINGS["postgres"]["database"] = config("PIXL_DB_NAME", default="pixl")


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
    api_name = f"{queue_name}_api"

    if api_name not in API_SETTINGS:
        msg = (
            f"Cannot update the rate for {queue_name}. {api_name} was"
            f" not specified in the configuration"
        )
        raise ValueError(msg)

    return APIConfig(API_SETTINGS[api_name])
