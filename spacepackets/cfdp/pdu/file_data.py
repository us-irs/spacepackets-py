from __future__ import annotations
import enum
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
        file_data: bytes,
        segment_metadata_flag: SegmentMetadataFlag,
        # These fields will only be present if the segment metadata flag is set
        record_continuation_state: RecordContinuationState,
        segment_metadata: bytes,
        offset: int,
        pdu_conf: PduConfig
    ):
        self.pdu_header = PduHeader(
            segment_metadata_flag=segment_metadata_flag,
            pdu_type=PduType.FILE_DATA,
            pdu_conf=pdu_conf,
            pdu_data_field_len=0
        )
        self.record_continuation_state = record_continuation_state
        self.segment_metadata_length = len(segment_metadata)
        self.segment_metadata = segment_metadata
        self.offset = offset
        self.file_data = file_data

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

    def pack(self) -> bytearray:
        file_data_pdu = self.pdu_header.pack()
        if self.pdu_header.segment_metadata_flag:
            if self.segment_metadata_length < 63:
                logger = get_console_logger()
                logger.warning(
                    f'Segment metadata length {self.segment_metadata_length} invalid, '
                    f'must be less than 63 bytes'
                )
                raise ValueError
            file_data_pdu.append(self.record_continuation_state << 6 | self.segment_metadata_length)
            file_data_pdu.extend(self.segment_metadata)
        if not self.pdu_header.is_large_file():
            file_data_pdu.extend(struct.pack('!I', self.offset))
        else:
            file_data_pdu.extend(struct.pack('!Q', self.offset))
        file_data_pdu.extend(self.file_data)
        return file_data_pdu

    @classmethod
    def unpack(cls, raw_packet: bytearray) -> FileDataPdu:
        file_data_packet = cls.__empty()
        file_data_packet.pdu_header.unpack(raw_packet=raw_packet)
        current_idx = file_data_packet.pdu_header.get_header_len()
        if file_data_packet.pdu_header.segment_metadata_flag:
            file_data_packet.record_continuation_state = raw_packet[current_idx] & 0x80
            file_data_packet.segment_metadata_length = raw_packet[current_idx] & 0x3f
            current_idx += 1
            if current_idx + file_data_packet.segment_metadata_length >= len(raw_packet):
                logger = get_console_logger()
                logger.warning('Packet too short for detected segment data length size')
                raise ValueError
            file_data_packet.segment_metadata = \
                raw_packet[current_idx: current_idx + file_data_packet.segment_metadata_length]
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
        )
        current_idx += struct_arg_tuple[1]
        if current_idx < len(raw_packet):
            file_data_packet.file_data = raw_packet[current_idx:]
        return file_data_packet
