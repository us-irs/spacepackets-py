from __future__ import annotations

import copy
import struct
from typing import TYPE_CHECKING

import fastcrc

from spacepackets.cfdp import CrcFlag
from spacepackets.cfdp.conf import LargeFileFlag, PduConfig
from spacepackets.cfdp.defs import Direction
from spacepackets.cfdp.pdu.file_directive import (
    AbstractFileDirectiveBase,
    DirectiveType,
    FileDirectivePduBase,
)

if TYPE_CHECKING:
    from spacepackets.cfdp.pdu import PduHeader


class KeepAlivePdu(AbstractFileDirectiveBase):
    """Encapsulates the Keep Alive file directive PDU, see CCSDS 727.0-B-5 p.85"""

    def __init__(self, pdu_conf: PduConfig, progress: int):
        pdu_conf = copy.copy(pdu_conf)
        directive_param_field_len = 4
        if pdu_conf.file_flag == LargeFileFlag.LARGE:
            directive_param_field_len = 8
        if pdu_conf.crc_flag == CrcFlag.WITH_CRC:
            directive_param_field_len += 2
        pdu_conf.direction = Direction.TOWARDS_SENDER
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
    def file_flag(self) -> LargeFileFlag:
        return self.pdu_file_directive.pdu_header.file_flag

    @file_flag.setter
    def file_flag(self, file_size: LargeFileFlag) -> None:
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
        if self.pdu_file_directive.pdu_conf.crc_flag == CrcFlag.WITH_CRC:
            keep_alive_packet.extend(
                struct.pack("!H", fastcrc.crc16.ibm_3740(bytes(keep_alive_packet)))
            )
        return keep_alive_packet

    @classmethod
    def unpack(cls, data: bytes | bytearray) -> KeepAlivePdu:
        """Generate an object instance from raw data. Care should be taken to check whether
        the raw bytestream really contains a Keep Alive PDU.

        Raises
        --------

        BytesTooShortError
            Raw data too short for expected object.
        ValueError
            Invalid directive type or data format.
        InvalidCrcError
            PDU has a 16 bit CRC and the CRC check failed.
        """
        keep_alive_pdu = cls.__empty()
        keep_alive_pdu.pdu_file_directive = FileDirectivePduBase.unpack(raw_packet=data)
        keep_alive_pdu.pdu_file_directive.verify_length_and_checksum(data)
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
    def packet_len(self) -> int:
        return self.pdu_file_directive.packet_len

    def __eq__(self, other: object):
        if not isinstance(other, KeepAlivePdu):
            return False
        return (
            self.pdu_file_directive == other.pdu_file_directive and self.progress == other.progress
        )

    def __hash__(self) -> int:
        return hash(
            (
                self.pdu_file_directive,
                self.progress,
            )
        )

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(pdu_conf={self.pdu_file_directive.pdu_conf!r}, "
            f"progress={self.progress!r})"
        )
