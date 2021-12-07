from __future__ import annotations
import struct
from typing import Optional

from spacepackets.cfdp.pdu.file_directive import FileDirectivePduBase, DirectiveCodes
from spacepackets.cfdp.definitions import ConditionCode
from spacepackets.cfdp.conf import PduConfig
from spacepackets.cfdp.tlv import EntityIdTlv
from spacepackets.cfdp.conf import check_packet_length


class EofPdu:
    """Encapsulates the EOF file directive PDU, see CCSDS 727.0-B-5 p.79"""

    def __init__(
        self,
        file_checksum: bytes,
        file_size: int,
        pdu_conf: PduConfig,
        fault_location: Optional[EntityIdTlv] = None,
        condition_code: ConditionCode = ConditionCode.NO_ERROR,
    ):
        """Constructor for an EOF PDU

        :param file_checksum: 4 byte checksum
        :param file_size:
        :param pdu_conf:
        :param fault_location:
        :param condition_code:
        :raise ValueError: Invalid input, file checksum not 4 bytes long
        """
        if len(file_checksum) != 4:
            raise ValueError
        self.condition_code = condition_code
        self.file_checksum = file_checksum
        self.file_size = file_size
        self._fault_location = fault_location
        self.pdu_file_directive = FileDirectivePduBase(
            directive_code=DirectiveCodes.EOF_PDU,
            pdu_conf=pdu_conf,
            directive_param_field_len=0,
        )
        self._calculate_directive_param_field_len()

    @property
    def packet_len(self) -> int:
        return self.pdu_file_directive.packet_len

    @property
    def fault_location(self):
        return self._fault_location

    @fault_location.setter
    def fault_location(self, fault_location: Optional[EntityIdTlv]):
        self._fault_location = fault_location
        self._calculate_directive_param_field_len()

    def _calculate_directive_param_field_len(self):
        directive_param_field_len = 9
        if self.pdu_file_directive.pdu_header.is_large_file():
            directive_param_field_len = 13
        if self._fault_location is not None:
            directive_param_field_len += self._fault_location.packet_len
        self.pdu_file_directive.directive_param_field_len = directive_param_field_len

    @classmethod
    def __empty(cls) -> EofPdu:
        empty_conf = PduConfig.empty()
        return cls(
            file_checksum=bytes([0x00, 0x00, 0x00, 0x00]),
            file_size=0,
            pdu_conf=empty_conf,
        )

    def pack(self) -> bytearray:
        eof_pdu = self.pdu_file_directive.pack()
        eof_pdu.append(self.condition_code << 4)
        eof_pdu.extend(self.file_checksum)
        if self.pdu_file_directive.pdu_header.is_large_file():
            eof_pdu.extend(struct.pack("!Q", self.file_size))
        else:
            eof_pdu.extend(struct.pack("!I", self.file_size))
        if self.fault_location is not None:
            eof_pdu.extend(self.fault_location.pack())
        return eof_pdu

    @classmethod
    def unpack(cls, raw_packet: bytearray) -> EofPdu:
        """Deserialize raw EOF PDU packet
        :param raw_packet:
        :raise ValueError: If raw packet is too short
        :return:
        """
        eof_pdu = cls.__empty()
        eof_pdu.pdu_file_directive = FileDirectivePduBase.unpack(raw_packet=raw_packet)
        expected_min_len = eof_pdu.pdu_file_directive.header_len + 9
        if not check_packet_length(
            raw_packet_len=len(raw_packet), min_len=expected_min_len
        ):
            raise ValueError
        current_idx = eof_pdu.pdu_file_directive.header_len
        eof_pdu.condition_code = raw_packet[current_idx] & 0xF0
        expected_min_len = current_idx + 5
        current_idx += 1
        eof_pdu.file_checksum = raw_packet[current_idx : current_idx + 4]
        current_idx += 4
        current_idx, eof_pdu.file_size = eof_pdu.pdu_file_directive._parse_fss_field(
            raw_packet=raw_packet, current_idx=current_idx
        )
        if len(raw_packet) > current_idx:
            eof_pdu.fault_location = EntityIdTlv.unpack(
                raw_bytes=raw_packet[current_idx:]
            )
        return eof_pdu
