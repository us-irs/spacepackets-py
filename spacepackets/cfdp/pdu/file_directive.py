from __future__ import annotations

import abc
import enum
import struct

from spacepackets.cfdp.pdu.header import (
    PduHeader,
    PduType,
    SegmentMetadataFlag,
    AbstractPduBase,
)
from spacepackets.cfdp.defs import LargeFileFlag, CrcFlag
from spacepackets.cfdp.conf import PduConfig
from spacepackets.exceptions import BytesTooShortError
from spacepackets.util import UnsignedByteField


class DirectiveType(enum.IntEnum):
    EOF_PDU = 0x04
    FINISHED_PDU = 0x05
    ACK_PDU = 0x06
    METADATA_PDU = 0x07
    NAK_PDU = 0x08
    PROMPT_PDU = 0x09
    KEEP_ALIVE_PDU = 0x0C
    NONE = 0x0A


class AbstractFileDirectiveBase(AbstractPduBase):
    """Encapsulate common functions for classes which are PDU file directives"""

    @property
    @abc.abstractmethod
    def directive_type(self) -> DirectiveType:
        pass

    @property
    @abc.abstractmethod
    def pdu_header(self) -> PduHeader:
        # Could return abstract class here but I think returning the concrete implementation
        # provided here is ok..
        pass

    @property
    def pdu_type(self) -> PduType:
        return PduType.FILE_DIRECTIVE

    @property
    def file_flag(self) -> LargeFileFlag:
        return self.pdu_header.file_flag

    @file_flag.setter
    def file_flag(self, field_len: LargeFileFlag):
        self.pdu_header.file_flag = field_len

    @property
    def crc_flag(self):
        return self.pdu_header.crc_flag

    @crc_flag.setter
    def crc_flag(self, crc_flag: CrcFlag):
        self.pdu_header.crc_flag = crc_flag

    @property
    def pdu_data_field_len(self):
        return self.pdu_header.pdu_data_field_len

    @property
    def source_entity_id(self) -> UnsignedByteField:
        return self.pdu_header.source_entity_id

    @property
    def transaction_seq_num(self) -> UnsignedByteField:
        return self.pdu_header.transaction_seq_num

    @property
    def dest_entity_id(self) -> UnsignedByteField:
        return self.pdu_header.dest_entity_id

    @pdu_data_field_len.setter
    def pdu_data_field_len(self, pdu_data_field_len: int):
        self.pdu_header.pdu_data_field_len = pdu_data_field_len

    @property
    def header_len(self) -> int:
        """Returns the length of the PDU header plus the directive code octet length"""
        return self.pdu_header.header_len + 1

    @property
    def packet_len(self) -> int:
        """Get length of the packet when packing it
        :return:
        """
        return self.pdu_header.packet_len

    def __eq__(self, other: AbstractFileDirectiveBase):
        return (
            self.pdu_header == other.pdu_header
            and self.directive_type == other.directive_type
        )


class FileDirectivePduBase(AbstractFileDirectiveBase):
    """Base class for file directive PDUs encapsulating all its common components.
    All other file directive PDU classes implement this class
    """

    FILE_DIRECTIVE_PDU_LEN = 5

    def __init__(
        self,
        directive_code: DirectiveType,
        directive_param_field_len: int,
        pdu_conf: PduConfig,
    ):
        """Generic constructor for a file directive PDU. Most arguments are passed on the
        to build the generic PDU header.

        :param directive_code:
        :param directive_param_field_len: Length of the directive parameter field. The length of
            the PDU data field will be this length plus the one octet / byte of the directive code
        :param pdu_conf: Generic PDU transfer configuration
        """

        self._pdu_header = PduHeader(
            pdu_type=PduType.FILE_DIRECTIVE,
            pdu_data_field_len=directive_param_field_len + 1,
            pdu_conf=pdu_conf,
            # This flag is not relevant for file directive PDUs
            segment_metadata_flag=SegmentMetadataFlag.NOT_PRESENT,
        )
        self._directive_type = directive_code

    @property
    def pdu_conf(self) -> PduConfig:
        return self.pdu_header.pdu_conf

    @property
    def pdu_header(self) -> PduHeader:
        return self._pdu_header

    @property
    def directive_type(self) -> DirectiveType:
        return self._directive_type

    @property
    def directive_param_field_len(self):
        return self.pdu_header.pdu_data_field_len - 1

    @directive_param_field_len.setter
    def directive_param_field_len(self, directive_param_field_len: int):
        self.pdu_header.pdu_data_field_len = directive_param_field_len + 1

    @classmethod
    def __empty(cls) -> FileDirectivePduBase:
        empty_conf = PduConfig.empty()
        return cls(
            directive_code=DirectiveType.NONE,
            directive_param_field_len=0,
            pdu_conf=empty_conf,
        )

    def pack(self) -> bytearray:
        data = bytearray()
        data.extend(self.pdu_header.pack())
        data.append(self._directive_type)
        return data

    @classmethod
    def unpack(cls, raw_packet: bytes) -> FileDirectivePduBase:
        """Unpack a raw bytearray into the File Directive PDU object representation.

        :param raw_packet: Unpack PDU file directive base
        :raise BytesTooShortError: Passed bytearray is too short
        :return:
        """
        file_directive = cls.__empty()
        file_directive._pdu_header = PduHeader.unpack(data=raw_packet)
        # + 1 because a file directive has the directive code in addition to the PDU header
        header_len = file_directive.pdu_header.header_len + 1
        if header_len > len(raw_packet):
            raise BytesTooShortError(header_len, len(raw_packet))
        file_directive._directive_type = raw_packet[header_len - 1]
        return file_directive

    def _verify_file_len(self, file_size: int):
        """Can be used by subclasses to verify a given file size"""
        if self.pdu_header.file_flag == LargeFileFlag.LARGE and file_size > pow(2, 64):

            raise ValueError(f"File size {file_size} larger than 64 bit field")
        elif self.pdu_header.file_flag == LargeFileFlag.NORMAL and file_size > pow(
            2, 32
        ):
            raise ValueError(f"File size {file_size} larger than 32 bit field")

    def parse_fss_field(self, raw_packet: bytes, current_idx: int) -> (int, int):
        """Parse the FSS field, which has different size depending on the large file flag being
        set or not. Returns the current index incremented and the parsed file size.

        :raise ValueError: Packet not large enough
        """
        if self.pdu_header.file_flag == LargeFileFlag.LARGE:
            if current_idx + 8 > len(raw_packet):
                raise BytesTooShortError(current_idx + 8, len(raw_packet))
            file_size = struct.unpack("!Q", raw_packet[current_idx : current_idx + 8])[
                0
            ]
            current_idx += 8
        else:
            if current_idx + 4 > len(raw_packet):
                raise BytesTooShortError(current_idx + 4, len(raw_packet))
            file_size = struct.unpack("!I", raw_packet[current_idx : current_idx + 4])[
                0
            ]
            current_idx += 4
        return current_idx, file_size

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(directive_code={self.directive_type!r}, "
            f"directive_param_field_len={self.directive_param_field_len!r}, "
            f"pdu_conf={self.pdu_conf!r})"
        )

    def __eq__(self, other: FileDirectivePduBase):
        return AbstractFileDirectiveBase.__eq__(self, other)
