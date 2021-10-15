from __future__ import annotations
import struct
from typing import List, Optional, Type, Union

from spacepackets.cfdp.pdu.file_directive import FileDirectivePduBase, DirectiveCodes
from spacepackets.cfdp.conf import PduConfig, FileSize
from spacepackets.cfdp.tlv import CfdpTlv, TlvList
from spacepackets.cfdp.lv import CfdpLv
from spacepackets.cfdp.definitions import ChecksumTypes
from spacepackets.cfdp.conf import check_packet_length
from spacepackets.log import get_console_logger


class MetadataPdu:
    """Encapsulates the Keep Alive file directive PDU, see CCSDS 727.0-B-5 p.83"""

    def __init__(
        self,
        closure_requested: bool,
        checksum_type: ChecksumTypes,
        file_size: int,
        source_file_name: Optional[str],
        dest_file_name: Optional[str],
        pdu_conf: PduConfig,
        options: Optional[TlvList] = None,
    ):
        self.closure_requested = closure_requested
        self.checksum_type = checksum_type
        self.file_size = file_size
        if source_file_name is None:
            self._source_file_name_lv = CfdpLv(value=bytes())
        else:
            source_file_name_as_bytes = source_file_name.encode('utf-8')
            self._source_file_name_lv = CfdpLv(
                value=source_file_name_as_bytes
            )
        if dest_file_name is None:
            self._dest_file_name_lv = CfdpLv(value=bytes())
        else:
            dest_file_name_as_bytes = dest_file_name.encode('utf-8')
            self._dest_file_name_lv = CfdpLv(
                value=dest_file_name_as_bytes
            )
        if options is None:
            self._options = []
        else:
            self._options = options
        self.pdu_file_directive = FileDirectivePduBase(
            directive_code=DirectiveCodes.METADATA_PDU,
            pdu_conf=pdu_conf,
            directive_param_field_len=5
        )
        self._calculate_directive_field_len()

    @classmethod
    def __empty(cls) -> MetadataPdu:
        empty_conf = PduConfig.empty()
        return cls(
            closure_requested=False,
            checksum_type=ChecksumTypes.MODULAR,
            file_size=0,
            source_file_name="",
            dest_file_name="",
            pdu_conf=empty_conf
        )

    @property
    def options(self):
        return self._options

    @options.setter
    def options(self, options: Optional[List[CfdpTlv]]):
        if options is None:
            options = []
        self._options = options
        self._calculate_directive_field_len()

    @property
    def directive_param_field_len(self):
        return self.pdu_file_directive.directive_param_field_len

    def _calculate_directive_field_len(self):
        directive_param_field_len = 5
        if self.pdu_file_directive.pdu_header.is_large_file() == FileSize.LARGE:
            directive_param_field_len = 9
        directive_param_field_len += self._source_file_name_lv.packet_len
        directive_param_field_len += self._dest_file_name_lv.packet_len
        for option in self._options:
            directive_param_field_len += option.packet_len
        self.pdu_file_directive.directive_param_field_len = directive_param_field_len

    @property
    def source_file_name(self) -> str:
        return self._source_file_name_lv.value.decode()

    @source_file_name.setter
    def source_file_name(self, source_file_name: str):
        if source_file_name is None:
            self._source_file_name_lv = CfdpLv(value=bytes())
        else:
            source_file_name_as_bytes = source_file_name.encode('utf-8')
            self._source_file_name_lv = CfdpLv(
                value=source_file_name_as_bytes
            )
        self._calculate_directive_field_len()

    @property
    def dest_file_name(self) -> str:
        return self._dest_file_name_lv.value.decode()

    @dest_file_name.setter
    def dest_file_name(self, dest_file_name: str):
        if dest_file_name is None:
            self._dest_file_name_lv = CfdpLv(value=bytes())
        else:
            dest_file_name_as_bytes = dest_file_name.encode('utf-8')
            self._dest_file_name_lv = CfdpLv(
                value=dest_file_name_as_bytes
            )
        self._calculate_directive_field_len()

    @property
    def packet_len(self) -> int:
        return self.pdu_file_directive.packet_len

    def pack(self) -> bytearray:
        if not self.pdu_file_directive._verify_file_len(self.file_size):
            raise ValueError
        packet = self.pdu_file_directive.pack()
        packet.append((self.closure_requested << 6) | self.checksum_type)
        if self.pdu_file_directive.pdu_header.is_large_file():
            packet.extend(struct.pack('!Q', self.file_size))
        else:
            packet.extend(struct.pack('!I', self.file_size))
        packet.extend(self._source_file_name_lv.pack())
        packet.extend(self._dest_file_name_lv.pack())
        for option in self.options:
            packet.extend(option.pack())
        return packet

    @classmethod
    def unpack(cls, raw_packet: bytearray) -> MetadataPdu:
        metadata_pdu = cls.__empty()
        metadata_pdu.pdu_file_directive = FileDirectivePduBase.unpack(raw_packet=raw_packet)
        current_idx = metadata_pdu.pdu_file_directive.header_len
        # Minimal length: 1 byte + FSS (4 byte) + 2 empty LV (1 byte)
        if not check_packet_length(len(raw_packet), current_idx + 7):
            raise ValueError
        metadata_pdu.closure_requested = raw_packet[current_idx] & 0x40
        metadata_pdu.checksum_type = raw_packet[current_idx] & 0x0f
        current_idx += 1
        current_idx, metadata_pdu.file_size = metadata_pdu.pdu_file_directive._parse_fss_field(
            raw_packet=raw_packet, current_idx=current_idx
        )
        metadata_pdu._source_file_name_lv = CfdpLv.unpack(raw_bytes=raw_packet[current_idx:])
        current_idx += metadata_pdu._source_file_name_lv.packet_len
        metadata_pdu._dest_file_name_lv = CfdpLv.unpack(raw_bytes=raw_packet[current_idx:])
        current_idx += metadata_pdu._dest_file_name_lv.packet_len
        if current_idx < len(raw_packet):
            metadata_pdu._parse_options(raw_packet=raw_packet, start_idx=current_idx)
        return metadata_pdu

    def _parse_options(self, raw_packet: bytearray, start_idx: int):
        self._options = []
        current_idx = start_idx
        while True:
            current_tlv = CfdpTlv.unpack(raw_bytes=raw_packet[current_idx:])
            self._options.append(current_tlv)
            # This will always increment at least two, so we can't get stuck in the loop
            current_idx += current_tlv.packet_len
            if current_idx > len(raw_packet):
                # This can not really happen because the CFDP TLV should check the remaining packet
                # length as well. Still keep it for defensive proramming
                raise ValueError
            elif current_idx == len(raw_packet):
                break
