"""In case ECSS and CFDP code go into a separate pyton package, this layer can be adapted
to use a different logger (e.g. default logger)
"""
import logging
from typing import Union
from logging import Logger

__LOGGER = None
# By default, return root logger
__LOGGER_NAME: Union[str, None] = None
__LOGGER_CHANGED = False


def specify_custom_logger_name(logger_name: str):
    global __LOGGER_NAME, __LOGGER_CHANGED
    __LOGGER_NAME = logger_name
    __LOGGER_CHANGED = True


def get_console_logger() -> Logger:
    global __LOGGER, __LOGGER_NAME
    if __LOGGER is None or __LOGGER_CHANGED:
        __LOGGER = logging.getLogger(__LOGGER_NAME)
    return __LOGGER
