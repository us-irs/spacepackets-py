from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict

from spacepackets.cfdp.defs import (
    CrcFlag,
    Direction,
    LargeFileFlag,
    SegmentationControl,
    TransmissionMode,
)
from spacepackets.util import ByteFieldEmpty, ByteFieldU8, UnsignedByteField


@dataclass
class PduConfig:
    """Common configuration fields for a PDU."""

    source_entity_id: UnsignedByteField
    dest_entity_id: UnsignedByteField
    transaction_seq_num: UnsignedByteField
    trans_mode: TransmissionMode
    file_flag: LargeFileFlag = LargeFileFlag.NORMAL
    crc_flag: CrcFlag = CrcFlag.NO_CRC
    direction: Direction = Direction.TOWARDS_RECEIVER
    seg_ctrl: SegmentationControl = SegmentationControl.NO_RECORD_BOUNDARIES_PRESERVATION

    @classmethod
    def empty(cls) -> PduConfig:
        """Empty PDU configuration which is not valid for usage because the contained unsigned
        byte fields are empty (sequence number and both entity IDs)
        """
        return PduConfig(
            transaction_seq_num=ByteFieldEmpty(),
            trans_mode=TransmissionMode.ACKNOWLEDGED,
            source_entity_id=ByteFieldEmpty(),
            dest_entity_id=ByteFieldEmpty(),
            file_flag=LargeFileFlag.NORMAL,
            crc_flag=CrcFlag.NO_CRC,
        )

    @classmethod
    def default(cls) -> PduConfig:
        """Valid PDU configuration"""
        return PduConfig(
            transaction_seq_num=ByteFieldU8(0),
            trans_mode=TransmissionMode.ACKNOWLEDGED,
            source_entity_id=ByteFieldU8(0),
            dest_entity_id=ByteFieldU8(0),
            file_flag=LargeFileFlag.NORMAL,
            crc_flag=CrcFlag.NO_CRC,
        )

    def header_len(self) -> int:
        return (
            4
            + len(self.source_entity_id)
            + len(self.dest_entity_id)
            + len(self.transaction_seq_num)
        )


class CfdpDict(TypedDict):
    source_dest_entity_ids: tuple[bytes, bytes]


# TODO: Protect dict access with a dedicated lock for thread-safety
__CFDP_DICT: CfdpDict = {
    "source_dest_entity_ids": (b"", b""),
}


def set_entity_ids(source_entity_id: bytes, dest_entity_id: bytes) -> None:
    __CFDP_DICT["source_dest_entity_ids"] = (source_entity_id, dest_entity_id)


def get_entity_ids() -> tuple[bytes, bytes]:
    """Return a tuple where the first entry is the source entity ID"""
    return __CFDP_DICT["source_dest_entity_ids"]
