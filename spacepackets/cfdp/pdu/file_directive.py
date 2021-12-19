from __future__ import annotations
import enum
import struct

from spacepackets.cfdp.pdu.header import (
    PduHeader,
    PduType,
    SegmentMetadataFlag,
    HasPduHeader,
)
from spacepackets.cfdp.definitions import FileSize
from spacepackets.cfdp.conf import check_packet_length, PduConfig
from spacepackets.log import get_console_logger


class DirectiveCodes(enum.IntEnum):
    EOF_PDU = 0x04
    FINISHED_PDU = 0x05
    ACK_PDU = 0x06
    METADATA_PDU = 0x07
    NAK_PDU = 0x08
    PROMPT_PDU = 0x09
    KEEP_ALIVE_PDU = 0x0C
    NONE = 0x0A


class FileDirectivePduBase:
    FILE_DIRECTIVE_PDU_LEN = 5
    """Base class for file directive PDUs encapsulating all its common components.
    All other file directive PDU classes implement this class
    """

    def __init__(
        self,
        directive_code: DirectiveCodes,
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
        self.pdu_header = PduHeader(
            pdu_type=PduType.FILE_DIRECTIVE,
            pdu_data_field_len=directive_param_field_len + 1,
            pdu_conf=pdu_conf,
            # This flag is not relevant for file directive PDUs
            segment_metadata_flag=SegmentMetadataFlag.NOT_PRESENT,
        )
        self.directive_code = directive_code

    @property
    def pdu_data_field_len(self):
        return self.pdu_header.pdu_data_field_len

    @pdu_data_field_len.setter
    def pdu_data_field_len(self, pdu_data_field_len: int):
        self.pdu_header.pdu_data_field_len = pdu_data_field_len

    @property
    def directive_param_field_len(self):
        return self.pdu_header.pdu_data_field_len - 1

    @directive_param_field_len.setter
    def directive_param_field_len(self, directive_param_field_len: int):
        self.pdu_header.pdu_data_field_len = directive_param_field_len + 1

    def is_large_file(self):
        return self.pdu_header.is_large_file()

    @classmethod
    def __empty(cls) -> FileDirectivePduBase:
        empty_conf = PduConfig.empty()
        return cls(
            directive_code=DirectiveCodes.NONE,
            directive_param_field_len=0,
            pdu_conf=empty_conf,
        )

    @property
    def header_len(self) -> int:
        """Returns the length of the PDU header plus the directive code octet length"""
        return self.pdu_header.header_len + 1

    @property
    def packet_len(self) -> int:
        """Get length of the packet when packing it
        :return:
        """
        return self.pdu_header.pdu_len

    def pack(self) -> bytearray:
        data = bytearray()
        data.extend(self.pdu_header.pack())
        data.append(self.directive_code)
        return data

    @classmethod
    def unpack(cls, raw_packet: bytes) -> FileDirectivePduBase:
        """Unpack a raw bytearray into the File Directive PDU object representation
        :param raw_packet: Unpack PDU file directive base
        :raise ValueError: Passed bytearray is too short
        :return:
        """
        file_directive = cls.__empty()
        file_directive.pdu_header = PduHeader.unpack(raw_packet=raw_packet)
        # + 1 because a file directive has the directive code in addition to the PDU header
        header_len = file_directive.pdu_header.header_len + 1
        if not check_packet_length(raw_packet_len=len(raw_packet), min_len=header_len):
            raise ValueError
        file_directive.directive_code = raw_packet[header_len - 1]
        return file_directive

    def _verify_file_len(self, file_size: int) -> bool:
        """Can be used by subclasses to verify a given file size"""
        if self.pdu_header.pdu_conf.file_size == FileSize.LARGE and file_size > pow(
            2, 64
        ):
            logger = get_console_logger()
            logger.warning(f"File size {file_size} larger than 64 bit field")
            return False
        elif self.pdu_header.pdu_conf.file_size == FileSize.NORMAL and file_size > pow(
            2, 32
        ):
            logger = get_console_logger()
            logger.warning(f"File size {file_size} larger than 32 bit field")
            return False
        return True

    def _parse_fss_field(self, raw_packet: bytes, current_idx: int) -> (int, int):
        """Parse the FSS field, which has different size depending on the large file flag being
        set or not. Returns the current index incremented and the parsed file size
        :raise ValueError: Packet not large enough
        """
        if self.pdu_header.pdu_conf.file_size == FileSize.LARGE:
            if not check_packet_length(len(raw_packet), current_idx + 8):
                raise ValueError
            file_size = struct.unpack("!Q", raw_packet[current_idx : current_idx + 8])[
                0
            ]
            current_idx += 8
        else:
            if not check_packet_length(len(raw_packet), current_idx + 4):
                raise ValueError
            file_size = struct.unpack("!I", raw_packet[current_idx : current_idx + 4])[
                0
            ]
            current_idx += 4
        return current_idx, file_size


class IsFileDirective(HasPduHeader):
    """Encapsulate common functions for classes which are FileDirectives"""

    def __init__(self, pdu_file_directive: FileDirectivePduBase):
        self.pdu_file_directive = pdu_file_directive
        HasPduHeader.__init__(self, pdu_header=pdu_file_directive.pdu_header)
