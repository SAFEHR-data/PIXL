#  Copyright (c) 2022 University College London Hospitals NHS Foundation Trust
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

from functools import partial
from logging.config import dictConfig
from pathlib import Path
import pprint
import tempfile
from typing import Any, Dict

from environs import Env, EnvError

__all__ = [
    "dump_settings",
    "ENV",
    "DEBUG",
    "LOG_ROOT_DIR",
    "AZURE_KEY_VAULT_NAME",
    "AZURE_KEY_VAULT_SECRET_NAME",
]

# Set env vars in docker/common.env or the docker-compose.yml
# and override with a local.env file for local development
env_parser = Env()

env_file = Path(__file__).parent / "local.env"
if env_file.exists():
    env_parser.read_env(env_file.as_posix(), override=True, recurse=False)

DEBUG = env_parser.bool("DEBUG", True)

ENV = env_parser.str("ENV")
if ENV not in ("dev", "test", "staging", "prod"):
    raise RuntimeError(f"Unsupported environment: {ENV}")

try:
    LOG_ROOT_DIR = env_parser.str("LOG_ROOT_DIR")
except EnvError:
    LOG_ROOT_DIR = tempfile.gettempdir()

AZURE_KEY_VAULT_NAME = None
AZURE_KEY_VAULT_SECRET_NAME = None


if ENV != "test":
    AZURE_KEY_VAULT_NAME = env_parser.str("AZURE_KEY_VAULT_NAME")
    AZURE_KEY_VAULT_SECRET_NAME = env_parser.str("AZURE_KEY_VAULT_SECRET_NAME")

# Setup logging
standard_formatter = {
    "format": "[%(asctime)s] | %(levelname)-8s | "
    + "[%(name)s %(funcName)s:%(lineno)s] %(message)s",
    "datefmt": "%Y-%m-%d %H:%M:%S",
}
simple_formatter = {
    "format": "[%(asctime)s] | %(levelname)-8s | %(name)s | %(message)s",
    "datefmt": "%Y-%m-%d %H:%M:%S",
}
console_handler = {
    "level": "DEBUG",
    "class": "logging.StreamHandler",
    "stream": "ext://sys.stdout",  # log to container's `stdout`
    "formatter": "simple",
}
file_handler = {
    "level": "INFO",
    "class": "logging.handlers.TimedRotatingFileHandler",
    "filename": (Path(LOG_ROOT_DIR) / "hasher-api.log").as_posix(),
    "when": "d",
    "interval": 1,
    "backupCount": 30,
    "formatter": "standard",
}
conf = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"standard": standard_formatter, "simple": simple_formatter},
    "handlers": {"console": console_handler, "logfile": file_handler},
    "loggers": {
        "root": {
            "level": "INFO",
            "handlers": ["console"],
        },
        "hasher": {
            "level": "DEBUG",
            "handlers": ["console", "logfile"],
            "propagate": False,
        },
        "uvicorn": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
        "fastapi": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
    },
}

dictConfig(conf)


# Dump settings if in DEBUG mode
def _dump_settings(symbols: Dict[str, Any]) -> None:
    settings = {}
    for k, v in symbols.items():
        if k.isupper():
            settings[k] = v
        if "PASSWORD" in k:
            settings[k] = "********"
    print("Settings:")
    pp = pprint.PrettyPrinter(indent=2)
    pp.pprint(dict(sorted(settings.items())))
    if env_file.exists():
        print(f"Included settings from {env_file}")


dump_settings = partial(_dump_settings, symbols=globals())
