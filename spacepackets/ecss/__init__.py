from __future__ import annotations

from crcmod.predefined import mkPredefinedCrcFun

from .defs import PusService, PusVersion
from .fields import (
    PacketFieldBase,
    PacketFieldEnum,
    PacketFieldU8,
    PacketFieldU16,
    PacketFieldU32,
    PfcReal,
    PfcSigned,
    PfcUnsigned,
    Ptc,
)
from .pus_verificator import PusVerificator
from .req_id import RequestId
from .tc import PusTc, PusTcDataFieldHeader, PusTelecommand
from .tm import PusTelemetry, PusTm, PusTmSecondaryHeader

__all__ = [
    "PacketFieldBase",
    "PacketFieldEnum",
    "PacketFieldU8",
    "PacketFieldU16",
    "PacketFieldU32",
    "PfcReal",
    "PfcSigned",
    "PfcUnsigned",
    "Ptc",
    "PusService",
    "PusTc",
    "PusTcDataFieldHeader",
    "PusTelecommand",
    "PusTelemetry",
    "PusTm",
    "PusTmSecondaryHeader",
    "PusVerificator",
    "PusVersion",
    "RequestId",
]


def check_pus_crc(tc_packet: bytes | bytearray) -> bool:
    """Checks the CRC of a given raw PUS packet. It is expected that the passed packet is the exact
    raw PUS packet. Both TC and TM packets can be passed to this function because both packet
    formats have a CCITT-CRC16 at the last two bytes as specified in the PUS standard.

    :return: True if the CRC is valid, False otherwise.
    """
    crc_func = mkPredefinedCrcFun(crc_name="crc-ccitt-false")
    crc = crc_func(tc_packet)
    return crc == 0
