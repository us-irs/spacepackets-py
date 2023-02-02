from __future__ import annotations
import struct
from typing import List, Tuple, Optional

from spacepackets.cfdp.pdu import PduHeader
from spacepackets.cfdp.pdu.file_directive import (
    AbstractFileDirectiveBase,
    FileDirectivePduBase,
    DirectiveType,
    LargeFileFlag,
)
from spacepackets.cfdp.conf import PduConfig


class NakPdu(AbstractFileDirectiveBase):
    """Encapsulates the NAK file directive PDU, see CCSDS 727.0-B-5 p.84"""

    def __init__(
        self,
        start_of_scope: int,
        end_of_scope: int,
        pdu_conf: PduConfig,
        segment_requests: Optional[List[Tuple[int, int]]] = None,
    ):
        """Create a NAK PDU object instance

        :param start_of_scope:
        :param end_of_scope:
        :param pdu_conf: Common PDU configuration
        :param segment_requests: A list of segment request pair tuples, where the first entry of
            list element is the start offset and the second entry is the end offset. If the
            start and end offset are both 0, the metadata is re-requested.
        """
        self.pdu_file_directive = FileDirectivePduBase(
            directive_code=DirectiveType.ACK_PDU,
            directive_param_field_len=8,
            pdu_conf=pdu_conf,
        )
        # Calling this will also update the directive parameter field length
        self.segment_requests = segment_requests
        self.start_of_scope = start_of_scope
        self.end_of_scope = end_of_scope

    @classmethod
    def __empty(cls) -> NakPdu:
        empty_conf = PduConfig.empty()
        return cls(
            start_of_scope=0, end_of_scope=0, segment_requests=[], pdu_conf=empty_conf
        )

    @property
    def directive_type(self) -> DirectiveType:
        return DirectiveType.NAK_PDU

    @property
    def pdu_header(self) -> PduHeader:
        return self.pdu_file_directive.pdu_header

    @property
    def file_flag(self):
        return self.pdu_file_directive.file_flag

    @file_flag.setter
    def file_flag(self, file_flag: LargeFileFlag):
        """Set the file size. This changes the length of the packet when packed as well
        which is handled by this function"""
        self.pdu_file_directive.file_flag = file_flag
        if file_flag == LargeFileFlag.NORMAL:
            directive_param_field_len = 8 + len(self._segment_requests) * 8
        elif file_flag == LargeFileFlag.LARGE:
            directive_param_field_len = 16 + len(self._segment_requests) * 16
        else:
            raise ValueError("Invalid large file flag argument")
        self.pdu_file_directive.directive_param_field_len = directive_param_field_len

    @property
    def segment_requests(self):
        """An optional list of segment request pair tuples, where the first entry of
        list element is the start offset and the second entry is the end offset. If the
        start and end offset are both 0, the metadata is re-requested.
        """
        return self._segment_requests

    @segment_requests.setter
    def segment_requests(self, segment_requests: Optional[List[Tuple[int, int]]]):
        """Update the segment requests. This changes the length of the packet when packed as well
        which is handled by this function."""
        self._segment_requests = segment_requests
        if self._segment_requests is None:
            self._segment_requests = []
            return
        is_large_file = self.pdu_file_directive.pdu_header.large_file_flag_set
        if not is_large_file:
            directive_param_field_len = 8 + len(self._segment_requests) * 8
        else:
            directive_param_field_len = 16 + len(self._segment_requests) * 16
        self.pdu_file_directive.directive_param_field_len = directive_param_field_len

    def pack(self) -> bytearray:
        """Pack the NAK PDU.

        :raises ValueError: File sizes too large for non-large files
        """
        nak_pdu = self.pdu_file_directive.pack()
        if not self.pdu_file_directive.pdu_header.large_file_flag_set:
            if (
                self.start_of_scope > pow(2, 32) - 1
                or self.end_of_scope > pow(2, 32) - 1
            ):
                raise ValueError
            nak_pdu.extend(struct.pack("!I", self.start_of_scope))
            nak_pdu.extend(struct.pack("!I", self.end_of_scope))
        else:
            nak_pdu.extend(struct.pack("!Q", self.start_of_scope))
            nak_pdu.extend(struct.pack("!Q", self.end_of_scope))
        for segment_request in self._segment_requests:
            if not self.pdu_file_directive.pdu_header.large_file_flag_set:
                if (
                    segment_request[0] > pow(2, 32) - 1
                    or segment_request[1] > pow(2, 32) - 1
                ):
                    raise ValueError
                nak_pdu.extend(struct.pack("!I", segment_request[0]))
                nak_pdu.extend(struct.pack("!I", segment_request[1]))
            else:
                nak_pdu.extend(struct.pack("!Q", segment_request[0]))
                nak_pdu.extend(struct.pack("!Q", segment_request[1]))
        return nak_pdu

    @classmethod
    def unpack(cls, data: bytes) -> NakPdu:
        """
        :param data:
        :raises BytesTooShortError:
        :return:
        """
        nak_pdu = cls.__empty()
        nak_pdu.pdu_file_directive = FileDirectivePduBase.unpack(raw_packet=data)
        current_idx = nak_pdu.pdu_file_directive.header_len
        if not nak_pdu.pdu_file_directive.pdu_header.large_file_flag_set:
            struct_arg_tuple = ("!I", 4)
        else:
            struct_arg_tuple = ("!Q", 8)
        nak_pdu.start_of_scope = struct.unpack(
            struct_arg_tuple[0],
            data[current_idx : current_idx + struct_arg_tuple[1]],
        )[0]
        current_idx += struct_arg_tuple[1]
        nak_pdu.end_of_scope = struct.unpack(
            struct_arg_tuple[0],
            data[current_idx : current_idx + struct_arg_tuple[1]],
        )[0]
        current_idx += struct_arg_tuple[1]
        if current_idx < len(data):
            packet_size_check = (len(data) - current_idx) % (struct_arg_tuple[1] * 2)
            if packet_size_check != 0:
                raise ValueError(
                    f"Invalid size for remaining data, "
                    f"which should be a multiple of {struct_arg_tuple[1] * 2}"
                )
            segment_requests = []
            while current_idx < len(data):
                start_of_segment = struct.unpack(
                    struct_arg_tuple[0],
                    data[current_idx : current_idx + struct_arg_tuple[1]],
                )[0]
                current_idx += struct_arg_tuple[1]
                end_of_segment = struct.unpack(
                    struct_arg_tuple[0],
                    data[current_idx : current_idx + struct_arg_tuple[1]],
                )[0]

                tuple_entry = start_of_segment, end_of_segment
                current_idx += struct_arg_tuple[1]
                segment_requests.append(tuple_entry)
            nak_pdu.segment_requests = segment_requests
        return nak_pdu

    def __eq__(self, other: NakPdu):
        return (
            self.pdu_file_directive == other.pdu_file_directive
            and self._segment_requests == other._segment_requests
            and self.start_of_scope == other.start_of_scope
            and self.end_of_scope == other.end_of_scope
        )

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(start_of_scope={self.start_of_scope!r}, "
            f"end_of_scope={self.end_of_scope!r}, pdu_conf={self.pdu_file_directive.pdu_conf!r}"
            f"segment_requests={self.segment_requests!r})"
        )
