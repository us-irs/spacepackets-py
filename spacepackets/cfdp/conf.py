from __future__ import annotations
from dataclasses import dataclass, field
from typing import TypedDict, Tuple

from spacepackets.cfdp.definitions import (
    FileSize,
    TransmissionModes,
    CrcFlag,
    SegmentationControl,
    Direction,
)
from spacepackets.log import get_console_logger


@dataclass
class PduConfig:
    """Common configuration fields for a PDU.

    Setting the GLOBAL_CONFIG property or creating an empty configuration will automatically
    determine the flag values of the respective fields from the global configuration to avoid
    specifying parameter which rarely change repeatedly
    """

    transaction_seq_num: bytes
    trans_mode: TransmissionModes
    file_size: FileSize = FileSize.GLOBAL_CONFIG
    crc_flag: CrcFlag = CrcFlag.GLOBAL_CONFIG
    direction: Direction = Direction.TOWARDS_RECEIVER
    seg_ctrl: SegmentationControl = (
        SegmentationControl.NO_RECORD_BOUNDARIES_PRESERVATION
    )
    source_entity_id: bytes = bytes()
    dest_entity_id: bytes = bytes()

    @classmethod
    def empty(cls) -> PduConfig:
        return PduConfig(
            transaction_seq_num=bytes([0]),
            trans_mode=TransmissionModes.ACKNOWLEDGED,
            source_entity_id=bytes([0]),
            dest_entity_id=bytes([0]),
            file_size=FileSize.GLOBAL_CONFIG,
            crc_flag=CrcFlag.GLOBAL_CONFIG,
        )

    def __post_init__(self):
        """Ensure that the global configuration is converted to the actual value immediately"""
        if self.crc_flag == CrcFlag.GLOBAL_CONFIG:
            self.crc_flag = get_default_pdu_crc_mode()
        if self.file_size == FileSize.GLOBAL_CONFIG:
            self.file_size = get_default_file_size()


class CfdpDict(TypedDict):
    source_dest_entity_ids: Tuple[bytes, bytes]
    with_crc: CrcFlag
    file_size: FileSize


# TODO: Protect dict access with a dedicated lock for thread-safety
__CFDP_DICT: CfdpDict = {
    "source_dest_entity_ids": (bytes(), bytes()),
    "with_crc": CrcFlag.NO_CRC,
    "file_size": FileSize.NORMAL,
}


def set_default_pdu_crc_mode(with_crc: CrcFlag):
    __CFDP_DICT["with_crc"] = with_crc


def get_default_pdu_crc_mode() -> CrcFlag:
    return __CFDP_DICT["with_crc"]


def set_entity_ids(source_entity_id: bytes, dest_entity_id: bytes):
    __CFDP_DICT["source_dest_entity_ids"] = (source_entity_id, dest_entity_id)


def get_entity_ids() -> Tuple[bytes, bytes]:
    """Return a tuple where the first entry is the source entity ID"""
    return __CFDP_DICT["source_dest_entity_ids"]


def set_default_file_size(file_size: FileSize):
    __CFDP_DICT["file_size"] = file_size


def get_default_file_size() -> FileSize:
    return __CFDP_DICT["file_size"]


def check_packet_length(
    raw_packet_len: int, min_len: int, warn_on_fail: bool = True
) -> bool:
    """Check whether the length of a raw packet is shorter than a specified expected minimum length.
    By defaults, prints a warning if this is the case
    :param raw_packet_len:
    :param min_len:
    :param warn_on_fail:
    :return: Returns True if the raw packet is larger than the specified minimum length, False
    otherwise
    """
    if raw_packet_len < min_len:
        if warn_on_fail:
            logger = get_console_logger()
            logger.warning(
                f"Detected packet length {raw_packet_len}, smaller than expected {min_len}"
            )
        return False
    return True
