import logging

from spacepackets.ccsds import (
    PacketType,
    SequenceFlags,
    SpacePacket,
    SpacePacketHeader,
    SpHeader,
)
from spacepackets.exceptions import BytesTooShortError

__all__ = [
    "BytesTooShortError",
    "PacketType",
    "SequenceFlags",
    "SpHeader",
    "SpacePacket",
    "SpacePacketHeader",
]

__LIB_LOGGER = logging.getLogger(__name__)


def get_lib_logger() -> logging.Logger:
    """Get the library logger. Can be used to modify the library logs or disable the
    propagation."""
    return __LIB_LOGGER
