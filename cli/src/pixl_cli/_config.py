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

"""Configuration of CLI from environment variables."""

from pathlib import Path

from decouple import Config, RepositoryEmpty, RepositoryEnv

env_file = Path.cwd() / ".env"
config = Config(RepositoryEnv(env_file)) if env_file.exists() else Config(RepositoryEmpty())

# The PIXL root and export root directories from the point of view of the docker host (which
# is where the CLI runs). For the export directory within the export-api container, see
# pixl_export/main.py: EXPORT_API_EXPORT_ROOT_DIR
PIXL_ROOT = config(
    "PIXL_ROOT",
    default=Path(__file__).parents[3],
    cast=Path,
).resolve()

HOST_EXPORT_ROOT_DIR = config(
    "HOST_EXPORT_ROOT_DIR",
    default=Path(__file__).parents[3] / "projects" / "exports",
    cast=Path,
).resolve()

SERVICE_SETTINGS = {
    "rabbitmq": {
        "host": config("RABBITMQ_HOST"),
        "port": int(config("RABBITMQ_PORT")),
        "username": config("RABBITMQ_USERNAME"),
        "password": config("RABBITMQ_PASSWORD"),
    },
    "postgres": {
        "host": config("CLI_PIXL_DB_HOST"),
        "port": int(config("CLI_PIXL_DB_PORT")),
        "username": config("PIXL_DB_USER"),
        "password": config("PIXL_DB_PASSWORD"),
        "database": config("PIXL_DB_NAME"),
    },
}


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
    "export_api": APIConfig(
        host=config("PIXL_EXPORT_API_HOST"),
        port=int(config("PIXL_EXPORT_API_PORT")),
    ),
    "imaging_api": APIConfig(
        host=config("PIXL_IMAGING_API_HOST"),
        port=int(config("PIXL_IMAGING_API_PORT")),
        default_rate=float(config("PIXL_IMAGING_API_RATE", default=1)),
    ),
}


def api_config_for_queue(queue_name: str) -> APIConfig:
    """Configuration for an API associated with a queue"""
    api_name = {
        "export": "export_api",
        "imaging-primary": "imaging_api",
        "imaging-secondary": "imaging_api",
    }[queue_name]

    if api_name not in API_CONFIGS:
        msg = (
            f"Cannot update the rate for {queue_name}. {api_name} was"
            f" not specified in the configuration"
        )
        raise ValueError(msg)

    return API_CONFIGS[api_name]
