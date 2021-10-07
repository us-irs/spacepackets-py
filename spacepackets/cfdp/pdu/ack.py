from __future__ import annotations
import enum

from spacepackets.cfdp.pdu.file_directive import FileDirectivePduBase, DirectiveCodes, \
    ConditionCode
from spacepackets.cfdp.pdu.header import Direction, TransmissionModes, CrcFlag


class TransactionStatus(enum.IntEnum):
    """For more detailed information: CCSDS 727.0-B-5 p.81"""
    UNDEFINED = 0b00
    ACTIVE = 0b01
    TERMINATED = 0b10
    UNRECOGNIZED = 0b11


class AckPdu:
    """Encapsulates the ACK file directive PDU, see CCSDS 727.0-B-5 p.81"""

    def __init__(
        self,
        directive_code_of_acked_pdu: DirectiveCodes,
        condition_code_of_acked_pdu: ConditionCode,
        transaction_status: TransactionStatus,
        trans_mode: TransmissionModes,
        transaction_seq_num: bytes,
        direction: Direction = Direction.TOWARDS_RECEIVER,
        source_entity_id: bytes = bytes(),
        dest_entity_id: bytes = bytes(),
        crc_flag: CrcFlag = CrcFlag.GLOBAL_CONFIG,
    ):
        """Construct a ACK PDU object

        :param directive_code_of_acked_pdu:
        :param condition_code_of_acked_pdu:
        :param transaction_status:
        :param direction:
        :param trans_mode:
        :param transaction_seq_num:
        :param source_entity_id: If an empty bytearray is passed, the configured default value
            in the CFDP conf module will be used
        :param dest_entity_id: If an empty bytearray is passed, the configured default value
            in the CFDP conf module will be used
        :param crc_flag:
        :raises ValueError: Directive code invalid. Only EOF and Finished PDUs can be acknowledged
        """
        self.pdu_file_directive = FileDirectivePduBase(
            directive_code=DirectiveCodes.ACK_PDU,
            direction=direction,
            trans_mode=trans_mode,
            crc_flag=crc_flag,
            transaction_seq_num=transaction_seq_num,
            source_entity_id=source_entity_id,
            directive_param_field_len=2,
            dest_entity_id=dest_entity_id
        )
        if directive_code_of_acked_pdu not in [DirectiveCodes.FINISHED_PDU, DirectiveCodes.EOF_PDU]:
            raise ValueError
        self.directive_code_of_acked_pdu = directive_code_of_acked_pdu
        self.directive_subtype_code = 0
        if self.directive_code_of_acked_pdu == DirectiveCodes.FINISHED_PDU:
            self.directive_subtype_code = 0b0001
        else:
            self.directive_subtype_code = 0b0000
        self.condition_code_of_acked_pdu = condition_code_of_acked_pdu
        self.transaction_status = transaction_status

    def get_packed_len(self) -> int:
        return self.pdu_file_directive.get_packet_len()

    @classmethod
    def __empty(cls) -> AckPdu:
        return cls(
            # Still set valid directive code, otherwise ctor will explode
            directive_code_of_acked_pdu=DirectiveCodes.FINISHED_PDU,
            condition_code_of_acked_pdu=ConditionCode.NO_ERROR,
            transaction_status=TransactionStatus.UNDEFINED,
            direction=Direction.TOWARDS_SENDER,
            trans_mode=TransmissionModes.UNACKNOWLEDGED,
            transaction_seq_num=bytes([0]),
            source_entity_id=bytes([0]),
            dest_entity_id=bytes([0])
        )

    def pack(self) -> bytearray:
        packet = self.pdu_file_directive.pack()
        packet.append((self.directive_code_of_acked_pdu << 4) | self.directive_subtype_code)
        packet.append((self.condition_code_of_acked_pdu << 4) | self.transaction_status)
        return packet

    @classmethod
    def unpack(cls, raw_packet: bytearray) -> AckPdu:
        ack_packet = cls.__empty()
        ack_packet.pdu_file_directive = FileDirectivePduBase.unpack(raw_packet=raw_packet)
        current_idx = ack_packet.pdu_file_directive.get_packet_len()
        ack_packet.directive_code_of_acked_pdu = (raw_packet[current_idx] & 0xf0) >> 4
        ack_packet.directive_subtype_code = raw_packet[current_idx] & 0x0f
        current_idx += 1
        ack_packet.condition_code_of_acked_pdu = (raw_packet[current_idx] & 0xf0) >> 4
        ack_packet.transaction_status = raw_packet[current_idx] & 0x03
        return ack_packet
