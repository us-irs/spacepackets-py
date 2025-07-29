from __future__ import annotations

import dataclasses

from fastcrc import crc16

from spacepackets.ccsds.spacepacket import CCSDS_HEADER_LEN, SpacePacketHeader
from spacepackets.exceptions import BytesTooShortError, InvalidCrcCcitt16Error

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


@dataclasses.dataclass
class PacketInfo:
    sp_header: SpacePacketHeader
    pus_version: PusVersion


def peek_pus_packet_info(data: bytes | bytearray) -> PacketInfo:
    """Peeks the packet info from the given data.

    :raises InvalidCrcCcitt16Error: If the CRC-CCITT16 of the packet is invalid.
    :raises BytesTooShortError: If the provided data is too short to contain a valid PUS packet.
    :raises ValueError: Detected PUS verson is invalid.
    """
    sp_header = SpacePacketHeader.unpack(data=data)
    packet_len = sp_header.packet_len
    if crc16.ibm_3740(bytes(data[0:packet_len])) != 0:
        raise InvalidCrcCcitt16Error(bytes(data[0:packet_len]))
    raw_sec_header_first_byte = data[CCSDS_HEADER_LEN]
    if len(data) < packet_len:
        raise BytesTooShortError(expected_len=packet_len, bytes_len=len(data))
    pus_version = PusVersion((raw_sec_header_first_byte >> 4) & 0b111)
    packet_len = sp_header.packet_len
    return PacketInfo(sp_header, pus_version)


def check_pus_crc(packet: bytes | bytearray) -> bool:
    """Checks the CRC of a given raw PUS packet. It is expected that the passed packet is the exact
    raw PUS packet. Both TC and TM packets can be passed to this function because both packet
    formats have a CCITT-CRC16 at the last two bytes as specified in the PUS standard.

    :return: True if the CRC is valid, False otherwise.
    """
    return crc16.ibm_3740(bytes(packet)) == 0
