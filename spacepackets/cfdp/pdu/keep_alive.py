from __future__ import annotations

import struct

from spacepackets.cfdp.pdu import PduHeader
from spacepackets.cfdp.pdu.file_directive import (
    FileDirectivePduBase,
    DirectiveType,
    AbstractFileDirectiveBase,
)
from spacepackets.cfdp.conf import PduConfig, LargeFileFlag


class KeepAlivePdu(AbstractFileDirectiveBase):
    """Encapsulates the Keep Alive file directive PDU, see CCSDS 727.0-B-5 p.85"""

    def __init__(self, progress: int, pdu_conf: PduConfig):
        directive_param_field_len = 4
        if pdu_conf.file_flag == LargeFileFlag.LARGE:
            directive_param_field_len = 8
        # Directive param field length is minimum FSS size which is 4 bytes
        self.pdu_file_directive = FileDirectivePduBase(
            directive_code=DirectiveType.KEEP_ALIVE_PDU,
            pdu_conf=pdu_conf,
            directive_param_field_len=directive_param_field_len,
        )
        self.progress = progress

    @property
    def directive_type(self) -> DirectiveType:
        return DirectiveType.KEEP_ALIVE_PDU

    @property
    def pdu_header(self) -> PduHeader:
        return self.pdu_file_directive.pdu_header

    @property
    def file_flag(self):
        return self.pdu_file_directive.pdu_header.file_flag

    @file_flag.setter
    def file_flag(self, file_size: LargeFileFlag):
        directive_param_field_len = 4
        if file_size == LargeFileFlag.LARGE:
            directive_param_field_len = 8
        self.pdu_file_directive.pdu_header.file_flag = file_size
        self.pdu_file_directive.directive_param_field_len = directive_param_field_len

    @classmethod
    def __empty(cls) -> KeepAlivePdu:
        empty_conf = PduConfig.empty()
        return cls(progress=0, pdu_conf=empty_conf)

    def pack(self) -> bytearray:
        keep_alive_packet = self.pdu_file_directive.pack()
        if not self.pdu_file_directive.pdu_header.large_file_flag_set:
            if self.progress > pow(2, 32) - 1:
                raise ValueError
            keep_alive_packet.extend(struct.pack("I", self.progress))
        else:
            keep_alive_packet.extend(struct.pack("Q", self.progress))
        return keep_alive_packet

    @classmethod
    def unpack(cls, data: bytes) -> KeepAlivePdu:
        """
        :param data:
        :raises BytesTooShortError:
        :return:
        """
        keep_alive_pdu = cls.__empty()
        keep_alive_pdu.pdu_file_directive = FileDirectivePduBase.unpack(raw_packet=data)
        current_idx = keep_alive_pdu.pdu_file_directive.header_len
        if not keep_alive_pdu.pdu_file_directive.pdu_header.large_file_flag_set:
            struct_arg_tuple = ("!I", 4)
        else:
            struct_arg_tuple = ("!Q", 8)
        if (len(data) - current_idx) < struct_arg_tuple[1]:
            raise ValueError(f"invalid length {len(data)} for Keep Alive PDU")
        keep_alive_pdu.progress = struct.unpack(
            struct_arg_tuple[0],
            data[current_idx : current_idx + struct_arg_tuple[1]],
        )[0]
        return keep_alive_pdu

    @property
    def packet_len(self):
        return self.pdu_file_directive.packet_len

    def __eq__(self, other: KeepAlivePdu):
        return (
            self.pdu_file_directive == other.pdu_file_directive
            and self.progress == other.progress
        )

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(progress={self.progress!r}, "
            f"pdu_conf={self.pdu_file_directive.pdu_conf!r})"
        )
