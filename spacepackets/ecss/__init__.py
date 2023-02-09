from crcmod.predefined import mkPredefinedCrcFun

from .tc import PusVersion, PusTelecommand, PusTcDataFieldHeader
from .tm import PusTelemetry, PusTmSecondaryHeader
from .fields import (
    PacketFieldEnum,
    PacketFieldBase,
    PacketFieldU8,
    PacketFieldU16,
    PacketFieldU32,
    Ptc,
    PfcReal,
    PfcSigned,
    PfcUnsigned,
)
from .defs import PusService
from .req_id import RequestId
from .pus_verificator import PusVerificator


def check_pus_crc(tc_packet: bytes) -> bool:
    """Checks the CRC of a given raw PUS packet. It is expected that the passed packet is the exact
    raw PUS packet. Both TC and TM packets can be passed to this function because both packet
    formats have a CCITT-CRC16 at the last two bytes as specified in the PUS standard.

    :return: True if the CRC is valid, False otherwise.
    """
    crc_func = mkPredefinedCrcFun(crc_name="crc-ccitt-false")
    crc = crc_func(tc_packet)
    return crc == 0
