from __future__ import annotations
import enum
from dataclasses import dataclass
from typing import Union, Optional
import struct

from spacepackets.cfdp import LargeFileFlag
from spacepackets.cfdp.pdu.file_directive import SegmentMetadataFlag, PduType
from spacepackets.cfdp.conf import PduConfig
from spacepackets.cfdp.pdu.header import PduHeader, AbstractPduBase
from spacepackets.exceptions import BytesTooShortError
from spacepackets.util import UnsignedByteField


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
class FileDataParams:
    file_data: bytes
    offset: int
    segment_metadata_flag: Union[
        SegmentMetadataFlag, bool
    ] = SegmentMetadataFlag.NOT_PRESENT
    # These fields will only be present if the segment metadata flag is set
    record_cont_state: Optional[RecordContinuationState] = None
    segment_metadata: Optional[bytes] = None

    @classmethod
    def empty(cls) -> FileDataParams:
        return cls(file_data=bytes(), offset=0)


class FileDataPdu(AbstractPduBase):
    def __init__(self, params: FileDataParams, pdu_conf: PduConfig):
        self._params = params
        if isinstance(params.segment_metadata_flag, bool):
            self._params.segment_metadata_flag = SegmentMetadataFlag(
                params.segment_metadata_flag
            )
        else:
            self._params.segment_metadata_flag = params.segment_metadata_flag
        if (
            self._params.segment_metadata_flag == SegmentMetadataFlag.PRESENT
            and params.record_cont_state is None
        ):
            raise ValueError("Record continuation state must be specified")
        self.pdu_header = PduHeader(
            segment_metadata_flag=self._params.segment_metadata_flag,
            pdu_type=PduType.FILE_DATA,
            pdu_conf=pdu_conf,
            pdu_data_field_len=0,
        )
        self._calculate_pdu_data_field_len()

    @classmethod
    def __empty(cls) -> FileDataPdu:
        empty_conf = PduConfig.empty()
        return cls(
            params=FileDataParams.empty(),
            pdu_conf=empty_conf,
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
    def record_cont_state(self) -> Optional[RecordContinuationState]:
        return self._params.record_cont_state

    @property
    def offset(self):
        return self._params.offset

    @property
    def crc_flag(self):
        return self.pdu_header.crc_flag

    @property
    def has_segment_metadata(self) -> bool:
        return self._params.segment_metadata_flag == SegmentMetadataFlag.PRESENT

    @property
    def segment_metadata(self):
        return self._params.segment_metadata

    @segment_metadata.setter
    def segment_metadata(self, segment_metadata: bytes):
        self._params.segment_metadata = segment_metadata
        self._calculate_pdu_data_field_len()

    @property
    def file_data(self):
        return self._params.file_data

    @file_data.setter
    def file_data(self, file_data: bytes):
        self._params.file_data = file_data
        self._calculate_pdu_data_field_len()

    def _calculate_pdu_data_field_len(self):
        pdu_data_field_len = 0
        if self._params.segment_metadata_flag:
            pdu_data_field_len = 1 + len(self._params.segment_metadata)
        if self.pdu_header.large_file_flag_set:
            pdu_data_field_len += 8
        else:
            pdu_data_field_len += 4
        pdu_data_field_len += len(self._params.file_data)
        self.pdu_header.pdu_data_field_len = pdu_data_field_len

    def pack(self) -> bytearray:
        file_data_pdu = self.pdu_header.pack()
        if self.pdu_header.segment_metadata_flag:
            len_metadata = len(self._params.segment_metadata)
            if len_metadata > 63:
                raise ValueError(
                    f"Segment metadata length {len_metadata} invalid, larger than 63 bytes"
                )
            file_data_pdu.append(self._params.record_cont_state << 6 | len_metadata)
            if len_metadata > 0:
                file_data_pdu.extend(self._params.segment_metadata)
        if not self.pdu_header.large_file_flag_set:
            file_data_pdu.extend(struct.pack("!I", self._params.offset))
        else:
            file_data_pdu.extend(struct.pack("!Q", self._params.offset))
        file_data_pdu.extend(self._params.file_data)
        return file_data_pdu

    @classmethod
    def unpack(cls, data: bytes) -> FileDataPdu:
        """Create from raw bytes.

        :param data:
        :raises BytesTooShortError:
        :return:
        """
        file_data_packet = cls.__empty()
        file_data_packet.pdu_header = PduHeader.unpack(data=data)
        current_idx = file_data_packet.pdu_header.header_len
        if file_data_packet.pdu_header.segment_metadata_flag:
            file_data_packet._params.record_cont_state = RecordContinuationState(
                (data[current_idx] & 0xC0) >> 6
            )
            segment_metadata_len = data[current_idx] & 0x3F
            current_idx += 1
            if current_idx + segment_metadata_len >= len(data):
                raise BytesTooShortError(current_idx + segment_metadata_len, len(data))
            file_data_packet._params.segment_metadata = data[
                current_idx : current_idx + segment_metadata_len
            ]
            current_idx += segment_metadata_len
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
        if current_idx < len(data):
            file_data_packet._params.file_data = data[current_idx:]
        return file_data_packet

    @property
    def packet_len(self):
        return self.pdu_header.packet_len

    def __eq__(self, other: FileDataPdu):
        return self.pdu_header == other.pdu_header and self._params == other._params

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(params={self._params!r}, "
            f"pdu_conf={self.pdu_header.pdu_conf!r})"
        )
