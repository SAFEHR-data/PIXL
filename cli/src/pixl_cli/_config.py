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

SERVICE_SETTINGS = {
    "rabbitmq": {
        "host": config("RABBITMQ_HOST", default="localhost"),
        "port": int(config("RABBITMQ_PORT", default=7008)),
        "username": config("RABBITMQ_USERNAME", default="rabbitmq_username"),
        "password": config("RABBITMQ_PASSWORD", default="rabbitmq_password"),
    },
    "postgres": {
        "host": config("POSTGRES_HOST", default="localhost"),
        "port": int(config("POSTGRES_PORT", default=7001)),
        "username": config("PIXL_DB_USER", default="pixl_db_username"),
        "password": config("PIXL_DB_PASSWORD", default="pixl_db_password"),
        "database": config("PIXL_DB_NAME", default="pixl"),
    },
}  # type: dict


class APIConfig:
    """API Configuration"""

    def __init__(self, host: str, port: int, default_rate: float = 1) -> None:
        """Initialise the APIConfig class"""
        self.host = host
        self.port = port
        self.default_rate = default_rate

    @property
    def base_url(self) -> str:
        """Return the base url for the API"""
        return f"http://{self.host}:{self.port}"


API_CONFIGS = {
    "ehr_api": APIConfig(
        host=config("PIXL_EHR_API_HOST"),
        port=int(config("PIXL_EHR_API_PORT")),
        default_rate=float(config("PIXL_EHR_API_RATE", default=1)),
    ),
    "imaging_api": APIConfig(
        host=config("PIXL_IMAGING_API_HOST"),
        port=int(config("PIXL_IMAGING_API_PORT")),
        default_rate=float(config("PIXL_EHR_API_RATE", default=1)),
    )
}


def api_config_for_queue(queue_name: str) -> APIConfig:
    """Configuration for an API associated with a queue"""
    api_name = f"{queue_name}_api"

    if api_name not in API_CONFIGS:
        msg = (
            f"Cannot update the rate for {queue_name}. {api_name} was"
            f" not specified in the configuration"
        )
        raise ValueError(msg)

    return API_CONFIGS[api_name]
