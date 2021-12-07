from __future__ import annotations

import struct

from spacepackets.cfdp.pdu.file_directive import FileDirectivePduBase, DirectiveCodes
from spacepackets.cfdp.conf import PduConfig, FileSize, get_default_file_size
from spacepackets.log import get_console_logger


class KeepAlivePdu:
    """Encapsulates the Keep Alive file directive PDU, see CCSDS 727.0-B-5 p.85"""

    def __init__(self, progress: int, pdu_conf: PduConfig):
        directive_param_field_len = 4
        if pdu_conf.file_size == FileSize.NORMAL:
            directive_param_field_len = 4
        elif pdu_conf.file_size == FileSize.LARGE:
            directive_param_field_len = 8
        # Directive param field length is minimum FSS size which is 4 bytes
        self.pdu_file_directive = FileDirectivePduBase(
            directive_code=DirectiveCodes.KEEP_ALIVE_PDU,
            pdu_conf=pdu_conf,
            directive_param_field_len=directive_param_field_len,
        )
        self.progress = progress

    @property
    def file_size(self):
        return self.pdu_file_directive.pdu_header.file_size

    @file_size.setter
    def file_size(self, file_size: FileSize):
        if file_size == FileSize.GLOBAL_CONFIG:
            file_size = get_default_file_size()
        directive_param_field_len = 4
        if file_size == FileSize.NORMAL:
            directive_param_field_len = 4
        elif file_size == FileSize.LARGE:
            directive_param_field_len = 8
        self.pdu_file_directive.pdu_header.file_size = file_size
        self.pdu_file_directive.directive_param_field_len = directive_param_field_len

    @classmethod
    def __empty(cls) -> KeepAlivePdu:
        empty_conf = PduConfig.empty()
        return cls(progress=0, pdu_conf=empty_conf)

    def pack(self) -> bytearray:
        keep_alive_packet = self.pdu_file_directive.pack()
        if not self.pdu_file_directive.pdu_header.is_large_file():
            if self.progress > pow(2, 32) - 1:
                raise ValueError
            keep_alive_packet.extend(struct.pack("I", self.progress))
        else:
            keep_alive_packet.extend(struct.pack("Q", self.progress))
        return keep_alive_packet

    @classmethod
    def unpack(cls, raw_packet: bytearray) -> KeepAlivePdu:
        keep_alive_pdu = cls.__empty()
        keep_alive_pdu.pdu_file_directive = FileDirectivePduBase.unpack(
            raw_packet=raw_packet
        )
        current_idx = keep_alive_pdu.pdu_file_directive.header_len
        if not keep_alive_pdu.pdu_file_directive.pdu_header.is_large_file():
            struct_arg_tuple = ("!I", 4)
        else:
            struct_arg_tuple = ("!Q", 8)
        if (len(raw_packet) - current_idx) < struct_arg_tuple[1]:
            logger = get_console_logger()
            logger.warning(f"Invalid length {len(raw_packet)} for Keep Alive PDU")
            raise ValueError
        keep_alive_pdu.progress = struct.unpack(
            struct_arg_tuple[0],
            raw_packet[current_idx : current_idx + struct_arg_tuple[1]],
        )[0]
        return keep_alive_pdu

    @property
    def packet_len(self):
        return self.pdu_file_directive.packet_len
