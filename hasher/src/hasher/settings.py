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
]

# Set env vars in docker/common.env or the docker-compose.yml
# and override with a local .env file

env_parser = Env()

env_file = Path(__file__) / ".env"
if env_file.exists():
    env_parser.read_env(env_file.as_posix(), override=True, recurse=False)

DEBUG = env_parser.bool("DEBUG", False)

ENV = env_parser.str("PIXL_ENV")
if ENV not in ("dev", "test", "staging", "prod"):
    raise RuntimeError(f"Unsupported environment: {ENV}")

try:
    LOG_ROOT_DIR = env_parser.str("LOG_ROOT_DIR")
except EnvError:
    LOG_ROOT_DIR = tempfile.gettempdir()


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
