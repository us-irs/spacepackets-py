from __future__ import annotations
import struct


from spacepackets.cfdp.pdu.file_directive import FileDirectivePduBase, DirectiveCodes, \
    ConditionCode
from spacepackets.cfdp.pdu.header import Direction, TransmissionModes, CrcFlag
from spacepackets.cfdp.tlv import CfdpTlv
from spacepackets.cfdp.conf import check_packet_length


class EofPdu:
    """Encapsulates the EOF file directive PDU, see CCSDS 727.0-B-5 p.79"""
    MINIMAL_LENGTH = FileDirectivePduBase.FILE_DIRECTIVE_PDU_LEN + 1 + 4 + 4

    def __init__(
        self,
        file_checksum: int,
        file_size: int,
        direction: Direction,
        trans_mode: TransmissionModes,
        transaction_seq_num: bytes,
        crc_flag: CrcFlag = CrcFlag.GLOBAL_CONFIG,
        source_entity_id: bytes = bytes(),
        dest_entity_id: bytes = bytes(),
        fault_location: CfdpTlv = None,
        condition_code: ConditionCode = ConditionCode.NO_ERROR,
    ):
        self.pdu_file_directive = FileDirectivePduBase(
            directive_code=DirectiveCodes.EOF_PDU,
            direction=direction,
            trans_mode=trans_mode,
            crc_flag=crc_flag,
            transaction_seq_num=transaction_seq_num,
            source_entity_id=source_entity_id,
            dest_entity_id=dest_entity_id
        )
        self.condition_code = condition_code
        self.file_checksum = file_checksum
        self.file_size = file_size
        self.fault_location = fault_location

    @classmethod
    def __empty(cls) -> EofPdu:
        return cls(
            file_checksum=0,
            file_size=0,
            direction=Direction.TOWARDS_SENDER,
            trans_mode=TransmissionModes.UNACKNOWLEDGED,
            transaction_seq_num=bytes([0]),
        )

    def pack(self) -> bytearray:
        eof_pdu = bytearray()
        eof_pdu.extend(self.pdu_file_directive.pack())
        eof_pdu.append(self.condition_code << 4)
        eof_pdu.extend(struct.pack('!I', self.file_checksum))
        if self.pdu_file_directive.pdu_header.large_file:
            eof_pdu.extend(struct.pack('!Q', self.file_size))
        else:
            eof_pdu.extend(struct.pack('!I', self.file_size))
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
        expected_min_len = cls.MINIMAL_LENGTH
        if not check_packet_length(raw_packet_len=len(raw_packet), min_len=expected_min_len):
            raise ValueError
        current_idx = eof_pdu.pdu_file_directive.get_packet_len()
        eof_pdu.condition_code = raw_packet[current_idx] & 0xf0
        expected_min_len = current_idx + 5
        current_idx += 1
        checksum_raw = raw_packet[current_idx: current_idx + 4]
        eof_pdu.file_checksum = struct.unpack('!I', checksum_raw)[0]
        current_idx += 4
        current_idx, eof_pdu.file_size = eof_pdu.pdu_file_directive.parse_fss_field(
            raw_packet=raw_packet, current_idx=current_idx
        )
        if len(raw_packet) > current_idx:
            eof_pdu.fault_location = CfdpTlv.unpack(raw_bytes=raw_packet[current_idx:])
        return eof_pdu
