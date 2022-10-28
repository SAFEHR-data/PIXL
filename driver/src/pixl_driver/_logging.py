import logging

import coloredlogs

logger = logging.getLogger(__name__)
coloredlogs.install(level=logging.ERROR, logger=logger)


def set_log_level(level: str) -> None:
    coloredlogs.set_level(level)
