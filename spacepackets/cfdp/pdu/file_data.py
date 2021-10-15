from __future__ import annotations
import enum
from typing import Union
import struct

from spacepackets.cfdp.pdu.file_directive import SegmentMetadataFlag, PduType
from spacepackets.cfdp.conf import PduConfig
from spacepackets.cfdp.pdu.header import PduHeader
from spacepackets.log import get_console_logger


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


class FileDataPdu:
    def __init__(
        self,
        pdu_conf: PduConfig,
        file_data: bytes,
        offset: int,
        segment_metadata_flag: Union[SegmentMetadataFlag, bool],
        # These fields will only be present if the segment metadata flag is set
        record_continuation_state: RecordContinuationState = RecordContinuationState.START_AND_END,
        segment_metadata: bytes = bytes(),
    ):
        self.record_continuation_state = record_continuation_state
        if isinstance(segment_metadata_flag, bool):
            self.segment_metadata_flag = SegmentMetadataFlag(segment_metadata_flag)
        else:
            self.segment_metadata_flag = segment_metadata_flag
        self._segment_metadata = segment_metadata
        self.offset = offset
        self._file_data = file_data
        self.pdu_header = PduHeader(
            segment_metadata_flag=self.segment_metadata_flag,
            pdu_type=PduType.FILE_DATA,
            pdu_conf=pdu_conf,
            pdu_data_field_len=0
        )
        self._calculate_pdu_data_field_len()

    @classmethod
    def __empty(cls) -> FileDataPdu:
        empty_conf = PduConfig.empty()
        return cls(
            file_data=bytes(),
            segment_metadata_flag=SegmentMetadataFlag.NOT_PRESENT,
            segment_metadata=bytes(),
            record_continuation_state=RecordContinuationState.START_AND_END,
            offset=0,
            pdu_conf=empty_conf
        )

    @property
    def segment_metadata(self):
        return self._segment_metadata

    @segment_metadata.setter
    def segment_metadata(self, segment_metadata: bytes):
        self._segment_metadata = segment_metadata
        self._calculate_pdu_data_field_len()

    @property
    def file_data(self):
        return self._file_data

    @file_data.setter
    def file_data(self, file_data: bytes):
        self._file_data = file_data
        self._calculate_pdu_data_field_len()

    def _calculate_pdu_data_field_len(self):
        pdu_data_field_len = 0
        if self.segment_metadata_flag:
            pdu_data_field_len = 1 + len(self._segment_metadata)
        if self.pdu_header.is_large_file():
            pdu_data_field_len += 8
        else:
            pdu_data_field_len += 4
        pdu_data_field_len += len(self._file_data)
        self.pdu_header.pdu_data_field_len = pdu_data_field_len

    def pack(self) -> bytearray:
        file_data_pdu = self.pdu_header.pack()
        if self.pdu_header.segment_metadata_flag:
            len_metadata = len(self._segment_metadata)
            if len_metadata > 63:
                logger = get_console_logger()
                logger.warning(
                    f'Segment metadata length {len_metadata} invalid, larger than 63 bytes'
                )
                raise ValueError
            file_data_pdu.append(self.record_continuation_state << 6 | len_metadata)
            if len_metadata > 0:
                file_data_pdu.extend(self._segment_metadata)
        if not self.pdu_header.is_large_file():
            file_data_pdu.extend(struct.pack('!I', self.offset))
        else:
            file_data_pdu.extend(struct.pack('!Q', self.offset))
        file_data_pdu.extend(self._file_data)
        return file_data_pdu

    @classmethod
    def unpack(cls, raw_packet: bytearray) -> FileDataPdu:
        file_data_packet = cls.__empty()
        file_data_packet.pdu_header = PduHeader.unpack(raw_packet=raw_packet)
        current_idx = file_data_packet.pdu_header.header_len
        if file_data_packet.pdu_header.segment_metadata_flag:
            file_data_packet.record_continuation_state = RecordContinuationState(
                (raw_packet[current_idx] & 0xc0) >> 6
            )
            file_data_packet.segment_metadata_length = raw_packet[current_idx] & 0x3f
            current_idx += 1
            if current_idx + file_data_packet.segment_metadata_length >= len(raw_packet):
                logger = get_console_logger()
                logger.warning('Packet too short for detected segment data length size')
                raise ValueError
            file_data_packet.segment_metadata = \
                raw_packet[current_idx: current_idx + file_data_packet.segment_metadata_length]
            current_idx += file_data_packet.segment_metadata_length
        if not file_data_packet.pdu_header.is_large_file():
            struct_arg_tuple = ('!I', 4)
        else:
            struct_arg_tuple = ('!Q', 8)
        if current_idx + struct_arg_tuple[1] >= len(raw_packet):
            logger = get_console_logger()
            logger.warning('Packet too small to accommodate offset')
            raise ValueError
        file_data_packet.offset = struct.unpack(
            struct_arg_tuple[0], raw_packet[current_idx: current_idx + struct_arg_tuple[1]]
        )[0]
        current_idx += struct_arg_tuple[1]
        if current_idx < len(raw_packet):
            file_data_packet.file_data = raw_packet[current_idx:]
        return file_data_packet

    @property
    def packet_len(self):
        return self.pdu_header.pdu_len
