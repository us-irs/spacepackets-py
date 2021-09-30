"""Logging facilities to log warnings
"""
import logging
from spacepackets import __name__ as package_name
from typing import Union
from logging import Logger

__LOGGER = None
# By default, return package specific logger
__LOGGER_NAME: Union[str, None] = package_name
__LOGGER_CHANGED = False


def specify_custom_console_logger_name(logger_name: str):
    """If the user uses a special console logger, the name can be specified here. The spacepackets
    package will then use this logger as well. Otherwise, the package will use a package specific
    logger"""
    global __LOGGER_NAME, __LOGGER_CHANGED
    __LOGGER_NAME = logger_name
    __LOGGER_CHANGED = True


def get_console_logger() -> Logger:
    global __LOGGER, __LOGGER_NAME
    if __LOGGER is None or __LOGGER_CHANGED:
        __LOGGER = logging.getLogger(__LOGGER_NAME)
    return __LOGGER
