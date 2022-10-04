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

from pathlib import Path
import pprint
import tempfile
from typing import Any, Dict

from environs import Env, EnvError

__all__ = [
    "dump_settings",
    "env_parser",
    "ENV",
    "DEBUG",
    "LOG_ROOT_DIR",
    "AZ_APP_ID",
    "AZ_TENANT_ID",
    "AZ_NAME",
    "AZ_APP_PASSWORD"
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

AZ_APP_ID = env_parser.str("AZ_APP_ID")
AZ_TENANT_ID = env_parser.str("AZ_TENANT_ID")
AZ_NAME = env_parser.str("AZ_NAME")
AZ_APP_PASSWORD = env_parser.str("AZ_APP_PASSWORD")


def dump_settings(symbols: Dict[str, Any]) -> None:
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


if DEBUG:
    dump_settings(globals())
