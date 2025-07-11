from __future__ import annotations

import copy
import enum
import struct
from dataclasses import dataclass
from typing import TYPE_CHECKING

import fastcrc

from spacepackets.cfdp import CrcFlag, LargeFileFlag
from spacepackets.cfdp.conf import PduConfig
from spacepackets.cfdp.defs import Direction, TransmissionMode
from spacepackets.cfdp.pdu.file_directive import PduType, SegmentMetadataFlag
from spacepackets.cfdp.pdu.header import AbstractPduBase, PduHeader
from spacepackets.exceptions import BytesTooShortError

if TYPE_CHECKING:
    from spacepackets.util import UnsignedByteField


def get_max_file_seg_len_for_max_packet_len_and_pdu_cfg(
    pdu_conf: PduConfig,
    max_packet_len: int,
    segment_metadata: SegmentMetadata | None = None,
) -> int:
    """This function can be used to calculate the maximum allowed file segment size for
    a given maximum packet length and the segment metadata if there is any."""
    subtract = pdu_conf.header_len()
    if segment_metadata is not None:
        subtract += 1 + len(segment_metadata.metadata)
    if pdu_conf.file_flag == LargeFileFlag.LARGE:
        subtract += 8
    else:
        subtract += 4
    if pdu_conf.crc_flag == CrcFlag.WITH_CRC:
        subtract += 2
    if max_packet_len < subtract:
        raise ValueError(f"max packet length {max_packet_len} can not even hold base packet")
    return max_packet_len - subtract


class RecordContinuationState(enum.IntEnum):
    # If the PDU header's segmentation control flag is 1, this value indicates that the file
    # data is the continuation of a record begun in a prior PDU
    NO_START_NO_END = 0b00
    # Contains first octet of a record but not the end
    START_WITHOUT_END = 0b01
    # Contains end of a record but not the start
    END_WITHOUT_START = 0b10
    # Contains start and end of a record. It is also possible to include multiple complete records,
    # but the identification of boundaries is then an application matter
    # (e.g. use segment metadata field)
    START_AND_END = 0b11


@dataclass
class SegmentMetadata:
    record_cont_state: RecordContinuationState
    metadata: bytes


@dataclass
class FileDataParams:
    file_data: bytes
    offset: int
    segment_metadata: SegmentMetadata | None = None

    @classmethod
    def empty(cls) -> FileDataParams:
        return cls(file_data=b"", offset=0)


class FileDataPdu(AbstractPduBase):
    def __init__(self, pdu_conf: PduConfig, params: FileDataParams):
        self._params = params
        pdu_conf = copy.copy(pdu_conf)
        pdu_conf.direction = Direction.TOWARDS_RECEIVER
        seg_metadata_flag = SegmentMetadataFlag.NOT_PRESENT
        if self._params.segment_metadata is not None:
            seg_metadata_flag = SegmentMetadataFlag.PRESENT
        self._pdu_header = PduHeader(
            segment_metadata_flag=seg_metadata_flag,
            pdu_type=PduType.FILE_DATA,
            pdu_conf=pdu_conf,
            pdu_data_field_len=0,
        )
        self._calculate_pdu_data_field_len()

    @property
    def pdu_header(self) -> PduHeader:
        return self._pdu_header

    @classmethod
    def __empty(cls) -> FileDataPdu:
        empty_conf = PduConfig.empty()
        return cls(
            params=FileDataParams.empty(),
            pdu_conf=empty_conf,
        )

    def get_max_file_seg_len_for_max_packet_len(self, max_packet_len: int) -> int:
        """This simply calls :py:func:`get_max_file_seg_len_for_max_packet_len_and_pdu_cfg` with
        the correct arguments derived from the internal fields."""
        return get_max_file_seg_len_for_max_packet_len_and_pdu_cfg(
            self._pdu_header.pdu_conf, max_packet_len, self.segment_metadata
        )

    @property
    def header_len(self) -> int:
        return self.pdu_header.header_len

    @property
    def pdu_data_field_len(self) -> int:
        return self.pdu_header.pdu_data_field_len

    @property
    def pdu_type(self) -> PduType:
        return self.pdu_header.pdu_type

    @property
    def transmission_mode(self) -> TransmissionMode:
        return self.pdu_header.transmission_mode

    @property
    def direction(self) -> Direction:
        return self.pdu_header.direction

    @property
    def file_flag(self) -> LargeFileFlag:
        return self.pdu_header.file_flag

    @property
    def transaction_seq_num(self) -> UnsignedByteField:
        return self.pdu_header.transaction_seq_num

    @property
    def source_entity_id(self) -> UnsignedByteField:
        return self.pdu_header.source_entity_id

    @property
    def dest_entity_id(self) -> UnsignedByteField:
        return self.pdu_header.dest_entity_id

    @property
    def record_cont_state(self) -> RecordContinuationState | None:
        if self._params.segment_metadata is None:
            return None
        return self._params.segment_metadata.record_cont_state

    @property
    def offset(self) -> int:
        return self._params.offset

    @property
    def crc_flag(self) -> CrcFlag:
        return self.pdu_header.crc_flag

    @property
    def has_segment_metadata(self) -> bool:
        return self._pdu_header.segment_metadata_flag == SegmentMetadataFlag.PRESENT

    @property
    def segment_metadata(self) -> SegmentMetadata | None:
        return self._params.segment_metadata

    @segment_metadata.setter
    def segment_metadata(self, segment_metadata: SegmentMetadata | None) -> None:
        self._params.segment_metadata = segment_metadata
        if segment_metadata is None:
            self._pdu_header.segment_metadata_flag = SegmentMetadataFlag.NOT_PRESENT
        else:
            self._pdu_header.segment_metadata_flag = SegmentMetadataFlag.PRESENT
        self._calculate_pdu_data_field_len()

    @property
    def file_data(self) -> bytes:
        return self._params.file_data

    @file_data.setter
    def file_data(self, file_data: bytes) -> None:
        self._params.file_data = file_data
        self._calculate_pdu_data_field_len()

    def _calculate_pdu_data_field_len(self) -> None:
        pdu_data_field_len = 0
        if self.segment_metadata is not None:
            pdu_data_field_len = 1 + len(self.segment_metadata.metadata)
        if self.pdu_header.large_file_flag_set:
            pdu_data_field_len += 8
        else:
            pdu_data_field_len += 4
        pdu_data_field_len += len(self._params.file_data)
        if self.pdu_header.pdu_conf.crc_flag == CrcFlag.WITH_CRC:
            pdu_data_field_len += 2
        self.pdu_header.pdu_data_field_len = pdu_data_field_len

    def pack(self) -> bytearray:
        file_data_pdu = self.pdu_header.pack()
        if self.segment_metadata is not None:
            len_metadata = len(self.segment_metadata.metadata)
            if len_metadata > 63:
                raise ValueError(
                    f"Segment metadata length {len_metadata} invalid, larger than 63 bytes"
                )
            file_data_pdu.append(self.segment_metadata.record_cont_state << 6 | len_metadata)
            if len_metadata > 0:
                file_data_pdu.extend(self.segment_metadata.metadata)
        if not self.pdu_header.large_file_flag_set:
            file_data_pdu.extend(struct.pack("!I", self._params.offset))
        else:
            file_data_pdu.extend(struct.pack("!Q", self._params.offset))
        file_data_pdu.extend(self._params.file_data)
        if self.pdu_header.crc_flag == CrcFlag.WITH_CRC:
            file_data_pdu.extend(struct.pack("!H", fastcrc.crc16.ibm_3740(bytes(file_data_pdu))))
        return file_data_pdu

    @classmethod
    def unpack(cls, data: bytes | bytearray) -> FileDataPdu:
        """Generate an object instance from raw data. Care should be taken to check whether
        the raw bytestream really contains a File Data PDU.

        Raises
        --------

        BytesTooShortError
            Raw data too short for expected object.
        ValueError
            Invalid PDU type or data format.
        InvalidCrc
            PDU has a 16 bit CRC and the CRC check failed.
        """
        file_data_packet = cls.__empty()
        file_data_packet._pdu_header = PduHeader.unpack(data=data)
        file_data_packet._pdu_header.verify_length_and_checksum(data)
        current_idx = file_data_packet.pdu_header.header_len
        if file_data_packet.pdu_header.segment_metadata_flag:
            rec_cont_state = RecordContinuationState((data[current_idx] & 0xC0) >> 6)
            segment_metadata_len = data[current_idx] & 0x3F
            current_idx += 1
            if current_idx + segment_metadata_len >= len(data):
                raise BytesTooShortError(current_idx + segment_metadata_len, len(data))
            metadata = data[current_idx : current_idx + segment_metadata_len]
            current_idx += segment_metadata_len
            file_data_packet.segment_metadata = SegmentMetadata(
                record_cont_state=rec_cont_state, metadata=bytes(metadata)
            )
        if not file_data_packet.pdu_header.large_file_flag_set:
            struct_arg_tuple = ("!I", 4)
        else:
            struct_arg_tuple = ("!Q", 8)
        if current_idx + struct_arg_tuple[1] >= len(data):
            raise ValueError("Packet too small to accommodate offset")
        file_data_packet._params.offset = struct.unpack(
            struct_arg_tuple[0],
            data[current_idx : current_idx + struct_arg_tuple[1]],
        )[0]
        current_idx += struct_arg_tuple[1]

        if file_data_packet.pdu_header.crc_flag == CrcFlag.WITH_CRC:
            data = data[:-2]
        if current_idx < len(data):
            file_data_packet._params.file_data = bytes(data[current_idx:])
        return file_data_packet

    @property
    def packet_len(self) -> int:
        return self.pdu_header.packet_len

    def __eq__(self, other: object):
        if not isinstance(other, FileDataPdu):
            return False
        return self.pdu_header == other.pdu_header and self._params == other._params

    def __hash__(self) -> int:
        return hash(
            (
                self.pdu_header,
                self._params.file_data,
                self._params.offset,
                self._params.segment_metadata,
            )
        )

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(params={self._params!r}, "
            f"pdu_conf={self.pdu_header.pdu_conf!r})"
        )
