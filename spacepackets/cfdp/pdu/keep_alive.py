from __future__ import annotations

import struct

from spacepackets.cfdp.pdu.file_directive import FileDirectivePduBase, DirectiveCodes, Direction, \
    TransmissionModes, CrcFlag
from spacepackets.log import get_console_logger


class KeepAlivePdu:
    """Encapsulates the Keep Alive file directive PDU, see CCSDS 727.0-B-5 p.85"""

    def __init__(
        self,
        progress: int,
        # PDU file directive arguments

        trans_mode: TransmissionModes,
        transaction_seq_num: bytes,
        direction: Direction = Direction.TOWARDS_RECEIVER,
        crc_flag: CrcFlag = CrcFlag.GLOBAL_CONFIG,
        source_entity_id: bytes = bytes(),
        dest_entity_id: bytes = bytes(),
    ):
        self.pdu_file_directive = FileDirectivePduBase(
            directive_code=DirectiveCodes.KEEP_ALIVE_PDU,
            direction=direction,
            trans_mode=trans_mode,
            crc_flag=crc_flag,
            transaction_seq_num=transaction_seq_num,
            source_entity_id=source_entity_id,
            dest_entity_id=dest_entity_id
        )
        self.progress = progress

    @classmethod
    def __empty(cls) -> KeepAlivePdu:
        return cls(
            progress=0,
            trans_mode=TransmissionModes.UNACKNOWLEDGED,
            transaction_seq_num=bytes([0]),
        )

    def pack(self) -> bytearray:
        keep_alive_packet = self.pdu_file_directive.pack()
        if not self.pdu_file_directive.pdu_header.large_file:
            if self.progress > pow(2, 32) - 1:
                raise ValueError
            keep_alive_packet.extend(struct.pack('I', self.progress))
        else:
            keep_alive_packet.extend(struct.pack('Q', self.progress))
        return keep_alive_packet

    @classmethod
    def unpack(cls, raw_packet: bytearray) -> KeepAlivePdu:
        keep_alive_pdu = cls.__empty()
        keep_alive_pdu.pdu_file_directive = FileDirectivePduBase.unpack(raw_packet=raw_packet)
        current_idx = keep_alive_pdu.pdu_file_directive.get_packet_len()
        if not keep_alive_pdu.pdu_file_directive.pdu_header.large_file:
            struct_arg_tuple = ('!I', 4)
        else:
            struct_arg_tuple = ('!Q', 8)
        if (len(raw_packet) - current_idx) < struct_arg_tuple[1]:
            logger = get_console_logger()
            logger.warning(f'Invalid length {len(raw_packet)} for Keep Alive PDU')
            raise ValueError
        keep_alive_pdu.progress = struct.unpack(
            struct_arg_tuple[0], raw_packet[current_idx: current_idx + struct_arg_tuple[1]]
        )
        return keep_alive_pdu
