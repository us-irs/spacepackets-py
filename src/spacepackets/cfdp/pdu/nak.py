from __future__ import annotations

import struct
from typing import TYPE_CHECKING

import fastcrc

from spacepackets.cfdp import CrcFlag
from spacepackets.cfdp.conf import PduConfig
from spacepackets.cfdp.defs import Direction
from spacepackets.cfdp.pdu.file_directive import (
    AbstractFileDirectiveBase,
    DirectiveType,
    FileDirectivePduBase,
    LargeFileFlag,
)

if TYPE_CHECKING:
    from spacepackets.cfdp.pdu import PduHeader


def get_max_seg_reqs_for_max_packet_size_and_pdu_cfg(
    max_packet_size: int, pdu_conf: PduConfig
) -> int:
    """This function can be used to retrieve the maximum amount of segment request given
    a PDU configuration to stay below a certain maximum packet size. This is useful
    to calculate how many NAK PDUs are required inside a NAK sequence.

    Raises
    ------
    ValueError
        Invalid large file flag derived from the PDU configuration, or maximum packet size
        is not even large enough to hold the base packet without any segment requests.

    """
    base_decrement = pdu_conf.header_len() + 1
    if pdu_conf.crc_flag:
        base_decrement += 2
    if pdu_conf.file_flag == LargeFileFlag.NORMAL:
        base_decrement += 8
    elif pdu_conf.file_flag == LargeFileFlag.LARGE:
        base_decrement += 16
    if max_packet_size < base_decrement:
        raise ValueError("maximum packet size too small to hold base packet")
    max_packet_size -= base_decrement
    if pdu_conf.file_flag == LargeFileFlag.NORMAL:
        return max_packet_size // 8
    if pdu_conf.file_flag == LargeFileFlag.LARGE:
        return max_packet_size // 16
    raise ValueError("Invalid large file flag argument")


class NakPdu(AbstractFileDirectiveBase):
    """Encapsulates the NAK file directive PDU, see CCSDS 727.0-B-5 p.84.

    Please note that there is a distinction between a NAK PDU, and a NAK sequence which might
    consist of multiple NAK PDUs. Generally, each NAK sequence will only consist of one NAK PDU,
    but might consist of multiple ones if one NAK PDU is not sufficient to send all missing
    segment requests while staying below a maximum allowed packet size for one PDU.

    The start of scope of a NAK sequence (not individual PDU!) can be one of the following:

    - 0 if this is the first NAK sequence.
    - 0 if the event which causes an issuance of the NAK PDU is the NAK timer expiry.
    - The end-of-scope of the previous NAK sequence for this file transaction.

    The end of scope of a NAK sequence (not individual PDU!) can be one of the following:

    - The whole file size if an EOF (No Error) PDU was already received.
    - The current reception progress at the time of the event that causes issuance of a NAK
      sequence.

    The start of scope for an individual NAK PDU is the start of scope of the NAK sequence for
    the first NAK PDU inside the sequence. For every other NAK PDU in the sequence, it is the
    end-of-scope of the previous NAK PDU.

    The end of scope for an individual NAK PDU is the end of scope of the NAK sequence for the
    last NAK PDU inside the sequence. For every other NAK PDU in the sequence, it is the
    end offset of the NAK PDU's last segment request.

    Examples
    ---------

    Re-request metadata NAK PDU:

    >>> nak_pdu = NakPdu(PduConfig.default(), 0, 0, [(0, 0)])
    >>> nak_pdu.start_of_scope
    0
    >>> nak_pdu.end_of_scope
    0
    >>> nak_pdu.segment_requests
    [(0, 0)]

    Re-request two file segments NAK PDU:

    >>> nak_pdu = NakPdu(PduConfig.default(), 0, 640, [(0, 128), (512, 640)])
    >>> nak_pdu.start_of_scope
    0
    >>> nak_pdu.end_of_scope
    640
    >>> nak_pdu.segment_requests
    [(0, 128), (512, 640)]
    """

    def __init__(
        self,
        pdu_conf: PduConfig,
        start_of_scope: int,
        end_of_scope: int,
        segment_requests: list[tuple[int, int]] | None = None,
    ):
        """Create a NAK PDU object instance.

        Arguments
        ----------
        pdu_conf:
            Common PDU configuration.
        start_of_scope:
            The value of this parameter depends on the start of the scope
            of the whole NAK sequence and on the position of this PDU inside the NAK sequence.
            See the class documentation for more details.
        end_of_scope:
            The value of this parameter depends on the end of the scope
            of the whole NAK sequence and on the position of this PDU inside the NAK sequence.
            See the class documentation for more details.
        segment_requests:
            A list of segment request pair tuples, where the first entry of
            list element is the start offset and the second entry is the end offset. If the
            start and end offset are both 0, the metadata is re-requested.
        """
        pdu_conf.direction = Direction.TOWARDS_SENDER
        self.pdu_file_directive = FileDirectivePduBase(
            directive_code=DirectiveType.NAK_PDU,
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
        return cls(start_of_scope=0, end_of_scope=0, segment_requests=[], pdu_conf=empty_conf)

    def get_max_seg_reqs_for_max_packet_size(self, max_packet_size: int) -> int:
        """Member method which forwards to
        :py:meth:`get_max_seg_reqs_for_max_packet_size_and_pdu_cfg`, passing the internal PDU
        configuration field."""
        return get_max_seg_reqs_for_max_packet_size_and_pdu_cfg(
            max_packet_size, self.pdu_file_directive.pdu_conf
        )

    @property
    def directive_type(self) -> DirectiveType:
        return DirectiveType.NAK_PDU

    @property
    def pdu_header(self) -> PduHeader:
        return self.pdu_file_directive.pdu_header

    @property
    def file_flag(self) -> LargeFileFlag:
        return self.pdu_file_directive.file_flag

    @file_flag.setter
    def file_flag(self, file_flag: LargeFileFlag) -> None:
        """Set the file size. This changes the length of the packet when packed as well
        which is handled by this function"""
        self.pdu_file_directive.file_flag = file_flag
        self._calculate_directive_field_len()

    def _calculate_directive_field_len(self) -> None:
        if self.pdu_file_directive.file_flag == LargeFileFlag.NORMAL:
            directive_param_field_len = 8 + len(self._segment_requests) * 8
        elif self.pdu_file_directive.file_flag == LargeFileFlag.LARGE:
            directive_param_field_len = 16 + len(self._segment_requests) * 16
        else:
            raise ValueError("Invalid large file flag argument")
        if self.pdu_file_directive.pdu_conf.crc_flag == CrcFlag.WITH_CRC:
            directive_param_field_len += 2
        self.pdu_file_directive.directive_param_field_len = directive_param_field_len

    @property
    def segment_requests(self) -> list[tuple[int, int]]:
        """An optional list of segment request pair tuples, where the first entry of
        list element is the start offset and the second entry is the end offset. If the
        start and end offset are both 0, the metadata is re-requested.
        """
        return self._segment_requests

    @segment_requests.setter
    def segment_requests(self, segment_requests: list[tuple[int, int]] | None) -> None:
        """Update the segment requests. This changes the length of the packet when packed as well
        which is handled by this function."""
        if segment_requests is None:
            self._segment_requests = []
        else:
            self._segment_requests: list[tuple[int, int]] = segment_requests  # type: ignore
        self._calculate_directive_field_len()

    def pack(self) -> bytearray:
        """Pack the NAK PDU.

        :raises ValueError: File sizes too large for non-large files
        """
        nak_pdu = self.pdu_file_directive.pack()
        if not self.pdu_file_directive.pdu_header.large_file_flag_set:
            if self.start_of_scope > pow(2, 32) - 1 or self.end_of_scope > pow(2, 32) - 1:
                raise ValueError
            nak_pdu.extend(struct.pack("!I", self.start_of_scope))
            nak_pdu.extend(struct.pack("!I", self.end_of_scope))
        else:
            nak_pdu.extend(struct.pack("!Q", self.start_of_scope))
            nak_pdu.extend(struct.pack("!Q", self.end_of_scope))
        for segment_request in self._segment_requests:
            if not self.pdu_file_directive.pdu_header.large_file_flag_set:
                if segment_request[0] > pow(2, 32) - 1 or segment_request[1] > pow(2, 32) - 1:
                    raise ValueError
                nak_pdu.extend(struct.pack("!I", segment_request[0]))
                nak_pdu.extend(struct.pack("!I", segment_request[1]))
            else:
                nak_pdu.extend(struct.pack("!Q", segment_request[0]))
                nak_pdu.extend(struct.pack("!Q", segment_request[1]))
        if self.pdu_file_directive.pdu_conf.crc_flag == CrcFlag.WITH_CRC:
            nak_pdu.extend(struct.pack("!H", fastcrc.crc16.ibm_3740(bytes(nak_pdu))))
        return nak_pdu

    @classmethod
    def unpack(cls, data: bytes | bytearray) -> NakPdu:
        """Generate an object instance from raw data. The user should take care to check whether
        the raw bytestream really contains a NAK PDU.

        Raises
        --------

        BytesTooShortError
            Raw data too short for expected object.
        ValueError
            Invalid directive type or data format.
        InvalidCrcError
            PDU has a 16 bit CRC and the CRC check failed.
        """
        nak_pdu = cls.__empty()
        nak_pdu.pdu_file_directive = FileDirectivePduBase.unpack(raw_packet=data)
        nak_pdu.pdu_file_directive.verify_length_and_checksum(data)
        if nak_pdu.pdu_file_directive.directive_type != DirectiveType.NAK_PDU:
            raise ValueError(
                f"invalid PDU directive type for NAK PDU: "
                f"{nak_pdu.pdu_file_directive.directive_type}"
            )
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
        end_of_segment_req_idx = len(data)
        if nak_pdu.pdu_header.crc_flag == CrcFlag.WITH_CRC:
            end_of_segment_req_idx -= 2
        if current_idx < end_of_segment_req_idx:
            packet_size_check = (end_of_segment_req_idx - current_idx) % (struct_arg_tuple[1] * 2)
            if packet_size_check != 0:
                raise ValueError(
                    "Invalid size for remaining data, "
                    f"which should be a multiple of {struct_arg_tuple[1] * 2}"
                )
            segment_requests = []
            while current_idx < end_of_segment_req_idx:
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

    def __eq__(self, other: object):
        if not isinstance(other, NakPdu):
            return False
        return (
            self.pdu_file_directive == other.pdu_file_directive
            and self._segment_requests == other._segment_requests
            and self.start_of_scope == other.start_of_scope
            and self.end_of_scope == other.end_of_scope
        )

    def __hash__(self) -> int:
        return hash(
            (
                self.pdu_file_directive,
                tuple(self._segment_requests),
                self.start_of_scope,
                self.end_of_scope,
            )
        )

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(start_of_scope={self.start_of_scope!r}, "
            f"end_of_scope={self.end_of_scope!r},"
            f" pdu_conf={self.pdu_file_directive.pdu_conf!r}"
            f"segment_requests={self.segment_requests!r})"
        )
