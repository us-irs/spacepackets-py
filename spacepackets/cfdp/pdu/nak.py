from __future__ import annotations
import struct
from typing import List, Tuple

from spacepackets.cfdp.pdu.file_directive import FileDirectivePduBase, DirectiveCodes
from spacepackets.cfdp.pdu.header import Direction, TransmissionModes, CrcFlag
from spacepackets.log import get_console_logger


class NakPdu:
    """Encapsulates the NAK file directive PDU, see CCSDS 727.0-B-5 p.84"""

    def __init__(
        self,
        start_of_scope: int,
        end_of_scope: int,
        # PDU file directive arguments
        trans_mode: TransmissionModes,
        segment_requests: List[Tuple[int, int]],
        transaction_seq_num: bytes,
        direction: Direction = Direction.TOWARDS_RECEIVER,
        crc_flag: CrcFlag = CrcFlag.GLOBAL_CONFIG,
        source_entity_id: bytes = bytes(),
        dest_entity_id: bytes = bytes(),
    ):
        self.pdu_file_directive = FileDirectivePduBase(
            directive_code=DirectiveCodes.ACK_PDU,
            direction=direction,
            trans_mode=trans_mode,
            crc_flag=crc_flag,
            transaction_seq_num=transaction_seq_num,
            source_entity_id=source_entity_id,
            dest_entity_id=dest_entity_id
        )
        self.start_of_scope = start_of_scope
        self.end_of_scope = end_of_scope
        self.segment_requests = segment_requests

    @classmethod
    def __empty(cls) -> NakPdu:
        return cls(
            trans_mode=TransmissionModes.UNACKNOWLEDGED,
            start_of_scope=0,
            end_of_scope=0,
            segment_requests=[],
            transaction_seq_num=bytes([0]),
        )

    def pack(self) -> bytearray:
        nak_pdu = self.pdu_file_directive.pack()
        if not self.pdu_file_directive.pdu_header.large_file:
            nak_pdu.extend(struct.pack('!I', self.start_of_scope))
            nak_pdu.extend(struct.pack('!I', self.end_of_scope))
        else:
            nak_pdu.extend(struct.pack('!Q', self.start_of_scope))
            nak_pdu.extend(struct.pack('!Q', self.end_of_scope))
        for segment_request in self.segment_requests:
            if not self.pdu_file_directive.pdu_header.large_file:
                nak_pdu.extend(struct.pack('!I', segment_request[0]))
                nak_pdu.extend(struct.pack('!I', segment_request[1]))
            else:
                nak_pdu.extend(struct.pack('!Q', segment_request[0]))
                nak_pdu.extend(struct.pack('!Q', segment_request[1]))
        return nak_pdu

    @classmethod
    def unpack(cls, raw_packet: bytearray) -> NakPdu:
        nak_pdu = cls.__empty()
        nak_pdu.pdu_file_directive = FileDirectivePduBase.unpack(raw_packet=raw_packet)
        current_idx = nak_pdu.pdu_file_directive.get_packet_len()
        if not nak_pdu.pdu_file_directive.pdu_header.large_file:
            struct_arg_tuple = ('!I', 4)
        else:
            struct_arg_tuple = ('!Q', 8)
        nak_pdu.start_of_scope = struct.unpack(
            struct_arg_tuple[0], raw_packet[current_idx: current_idx + struct_arg_tuple[1]]
        )
        current_idx += struct_arg_tuple[1]
        nak_pdu.end_of_scope = struct.unpack(
            struct_arg_tuple[0], raw_packet[current_idx: current_idx + struct_arg_tuple[1]]
        )
        current_idx += struct_arg_tuple[1]
        if current_idx < len(raw_packet):
            packet_size_check = ((len(raw_packet) - current_idx) % (struct_arg_tuple[1] * 2))
            if packet_size_check != 0:
                if current_idx >= len(raw_packet):
                    logger = get_console_logger()
                    logger.warning(
                        f'Invalid size for remaining data, '
                        f'which should be a multiple of {struct_arg_tuple[1] * 2}'
                    )
                    raise ValueError
            nak_pdu.segment_requests = []
            while current_idx < len(raw_packet):
                start_of_segment = (
                    struct.unpack(
                        struct_arg_tuple[0],
                        raw_packet[current_idx: current_idx + struct_arg_tuple[1]])
                )
                current_idx += struct_arg_tuple[1]
                end_of_segment = (
                    struct.unpack(
                        struct_arg_tuple[0],
                        raw_packet[current_idx: current_idx + struct_arg_tuple[1]])
                )
                tuple_entry = (start_of_segment, end_of_segment)
                nak_pdu.segment_requests.append(tuple_entry)
        return nak_pdu
