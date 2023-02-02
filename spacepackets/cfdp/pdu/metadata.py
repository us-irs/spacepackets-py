from __future__ import annotations

import dataclasses
import struct
from typing import List, Optional

from spacepackets.cfdp.pdu import PduHeader
from spacepackets.cfdp.pdu.file_directive import (
    FileDirectivePduBase,
    DirectiveType,
    AbstractFileDirectiveBase,
)
from spacepackets.cfdp.conf import PduConfig, LargeFileFlag
from spacepackets.cfdp.tlv import CfdpTlv, TlvList
from spacepackets.cfdp.lv import CfdpLv
from spacepackets.cfdp.defs import ChecksumType
from spacepackets.exceptions import BytesTooShortError


@dataclasses.dataclass
class MetadataParams:
    closure_requested: bool
    checksum_type: ChecksumType
    file_size: int
    source_file_name: Optional[str]
    dest_file_name: Optional[str]


class MetadataPdu(AbstractFileDirectiveBase):
    """Encapsulates the Metadata file directive PDU, see CCSDS 727.0-B-5 p.83"""

    def __init__(
        self,
        pdu_conf: PduConfig,
        params: MetadataParams,
        options: Optional[TlvList] = None,
    ):
        self.params = params
        if params.source_file_name is None:
            self._source_file_name_lv = CfdpLv(value=bytes())
        else:
            source_file_name_as_bytes = params.source_file_name.encode("utf-8")
            self._source_file_name_lv = CfdpLv(value=source_file_name_as_bytes)
        if params.dest_file_name is None:
            self._dest_file_name_lv = CfdpLv(value=bytes())
        else:
            dest_file_name_as_bytes = params.dest_file_name.encode("utf-8")
            self._dest_file_name_lv = CfdpLv(value=dest_file_name_as_bytes)
        self._options = options
        self.pdu_conf = pdu_conf
        self.pdu_file_directive = FileDirectivePduBase(
            directive_code=DirectiveType.METADATA_PDU,
            pdu_conf=pdu_conf,
            directive_param_field_len=5,
        )
        self._calculate_directive_field_len()

    @property
    def directive_type(self) -> DirectiveType:
        return DirectiveType.METADATA_PDU

    @property
    def pdu_header(self) -> PduHeader:
        return self.pdu_file_directive.pdu_header

    @property
    def closure_requested(self) -> bool:
        return self.params.closure_requested

    @property
    def file_size(self) -> int:
        """A value of 0 means this is an unbounded file, as opposed to no file. To check
        whether a Metadata PDU has no associated file, check :py:func:`source_file_name` against
        None"""
        return self.params.file_size

    @property
    def checksum_type(self) -> ChecksumType:
        return self.params.checksum_type

    @classmethod
    def __empty(cls) -> MetadataPdu:
        empty_conf = PduConfig.empty()
        return cls(
            params=MetadataParams(False, ChecksumType.MODULAR, 0, "", ""),
            pdu_conf=empty_conf,
        )

    @property
    def options(self) -> Optional[TlvList]:
        return self._options

    @options.setter
    def options(self, options: Optional[List[CfdpTlv]]):
        self._options = options
        self._calculate_directive_field_len()

    @property
    def directive_param_field_len(self):
        return self.pdu_file_directive.directive_param_field_len

    def _calculate_directive_field_len(self):
        directive_param_field_len = 5
        if (
            self.pdu_file_directive.pdu_header.large_file_flag_set
            == LargeFileFlag.LARGE
        ):
            directive_param_field_len = 9
        directive_param_field_len += self._source_file_name_lv.packet_len
        directive_param_field_len += self._dest_file_name_lv.packet_len
        if self._options is not None:
            for option in self._options:
                directive_param_field_len += option.packet_len
        self.pdu_file_directive.directive_param_field_len = directive_param_field_len

    @property
    def source_file_name(self) -> Optional[str]:
        """If there is no associated source file, for example for messages used for Proxy
        Operations, this function will return None
        """
        if self._source_file_name_lv.len == 0:
            return None
        return self._source_file_name_lv.value.decode()

    @source_file_name.setter
    def source_file_name(self, source_file_name: Optional[str]):
        if source_file_name is None:
            self._source_file_name_lv = CfdpLv(value=bytes())
        else:
            source_file_name_as_bytes = source_file_name.encode("utf-8")
            self._source_file_name_lv = CfdpLv(value=source_file_name_as_bytes)
        self._calculate_directive_field_len()

    @property
    def dest_file_name(self) -> Optional[str]:
        """If there is no associated source file, for example for messages used for Proxy
        Operations, this function will return None
        """
        if self._dest_file_name_lv.len == 0:
            return None
        return self._dest_file_name_lv.value.decode()

    @dest_file_name.setter
    def dest_file_name(self, dest_file_name: Optional[str]):
        if dest_file_name is None:
            self._dest_file_name_lv = CfdpLv(value=bytes())
        else:
            dest_file_name_as_bytes = dest_file_name.encode("utf-8")
            self._dest_file_name_lv = CfdpLv(value=dest_file_name_as_bytes)
        self._calculate_directive_field_len()

    @property
    def packet_len(self) -> int:
        return self.pdu_file_directive.packet_len

    def pack(self) -> bytearray:
        self.pdu_file_directive._verify_file_len(self.params.file_size)
        packet = self.pdu_file_directive.pack()
        packet.append((self.params.closure_requested << 6) | self.params.checksum_type)
        if self.pdu_file_directive.pdu_header.large_file_flag_set:
            packet.extend(struct.pack("!Q", self.params.file_size))
        else:
            packet.extend(struct.pack("!I", self.params.file_size))
        packet.extend(self._source_file_name_lv.pack())
        packet.extend(self._dest_file_name_lv.pack())
        if self._options is not None:
            for option in self.options:
                packet.extend(option.pack())
        return packet

    @classmethod
    def unpack(cls, data: bytes) -> MetadataPdu:
        """
        :param data:
        :raises BytesTooShortError:
        :return:
        """
        metadata_pdu = cls.__empty()

        metadata_pdu.pdu_file_directive = FileDirectivePduBase.unpack(raw_packet=data)
        current_idx = metadata_pdu.pdu_file_directive.header_len
        # Minimal length: 1 byte + FSS (4 byte) + 2 empty LV (1 byte)
        if current_idx + 7 > len(data):
            raise BytesTooShortError(current_idx + 7, len(data))
        params = MetadataParams(False, ChecksumType.MODULAR, 0, "", "")
        params.closure_requested = bool(data[current_idx] & 0x40)
        params.checksum_type = ChecksumType(data[current_idx] & 0x0F)
        current_idx += 1
        (
            current_idx,
            params.file_size,
        ) = metadata_pdu.pdu_file_directive.parse_fss_field(
            raw_packet=data, current_idx=current_idx
        )
        metadata_pdu.params = params
        metadata_pdu._source_file_name_lv = CfdpLv.unpack(raw_bytes=data[current_idx:])
        current_idx += metadata_pdu._source_file_name_lv.packet_len
        metadata_pdu._dest_file_name_lv = CfdpLv.unpack(raw_bytes=data[current_idx:])
        current_idx += metadata_pdu._dest_file_name_lv.packet_len
        if current_idx < len(data):
            metadata_pdu._parse_options(raw_packet=data, start_idx=current_idx)
        return metadata_pdu

    def _parse_options(self, raw_packet: bytes, start_idx: int):
        self._options = []
        current_idx = start_idx
        while True:
            current_tlv = CfdpTlv.unpack(data=raw_packet[current_idx:])
            self._options.append(current_tlv)
            # This will always increment at least two, so we can't get stuck in the loop
            current_idx += current_tlv.packet_len
            if current_idx > len(raw_packet):
                # This can not really happen because the CFDP TLV should check the remaining packet
                # length as well. Still keep it for defensive proramming
                raise ValueError
            elif current_idx == len(raw_packet):
                break

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(params={self.params!r}, options={self.options!r}, "
            f"pdu_conf={self.pdu_file_directive.pdu_conf})"
        )

    def __eq__(self, other: MetadataPdu):
        return (
            self.pdu_file_directive == other.pdu_file_directive
            and self.params.closure_requested == other.params.closure_requested
            and self.params.checksum_type == other.params.checksum_type
            and self.params.file_size == other.params.file_size
            and self._source_file_name_lv == other._source_file_name_lv
            and self._dest_file_name_lv == other._dest_file_name_lv
            and self._options == other._options
        )
