from __future__ import annotations
import enum

from spacepackets.cfdp.pdu import PduHeader
from spacepackets.cfdp.pdu.file_directive import (
    FileDirectivePduBase,
    DirectiveType,
    AbstractFileDirectiveBase,
)
from spacepackets.cfdp.defs import ConditionCode
from spacepackets.cfdp.conf import PduConfig


class TransactionStatus(enum.IntEnum):
    """For more detailed information: CCSDS 727.0-B-5 p.81"""

    UNDEFINED = 0b00
    ACTIVE = 0b01
    TERMINATED = 0b10
    UNRECOGNIZED = 0b11


class AckPdu(AbstractFileDirectiveBase):
    """Encapsulates the ACK file directive PDU, see CCSDS 727.0-B-5 p.81"""

    def __init__(
        self,
        directive_code_of_acked_pdu: DirectiveType,
        condition_code_of_acked_pdu: ConditionCode,
        transaction_status: TransactionStatus,
        pdu_conf: PduConfig,
    ):
        """Construct a ACK PDU object

        :param directive_code_of_acked_pdu:
        :param condition_code_of_acked_pdu:
        :param transaction_status:
        :param pdu_conf: PDU configuration parameters
        :raises ValueError: Directive code invalid. Only EOF and Finished PDUs can be acknowledged
        """
        self.pdu_file_directive = FileDirectivePduBase(
            directive_code=DirectiveType.ACK_PDU,
            directive_param_field_len=2,
            pdu_conf=pdu_conf,
        )
        if directive_code_of_acked_pdu not in [
            DirectiveType.FINISHED_PDU,
            DirectiveType.EOF_PDU,
        ]:
            raise ValueError(
                f"invalid directive code of acked PDU {directive_code_of_acked_pdu}"
            )
        self.directive_code_of_acked_pdu = directive_code_of_acked_pdu
        self.directive_subtype_code = 0
        if self.directive_code_of_acked_pdu == DirectiveType.FINISHED_PDU:
            self.directive_subtype_code = 0b0001
        else:
            self.directive_subtype_code = 0b0000
        self.condition_code_of_acked_pdu = condition_code_of_acked_pdu
        self.transaction_status = transaction_status

    @property
    def directive_type(self) -> DirectiveType:
        return DirectiveType.ACK_PDU

    @property
    def pdu_header(self) -> PduHeader:
        return self.pdu_file_directive.pdu_header

    def __eq__(self, other: AckPdu):
        return (
            self.pdu_file_directive == other.pdu_file_directive
            and self.directive_code_of_acked_pdu == other.directive_code_of_acked_pdu
            and self.directive_subtype_code == other.directive_subtype_code
            and self.condition_code_of_acked_pdu == other.condition_code_of_acked_pdu
            and self.transaction_status == other.transaction_status
        )

    @classmethod
    def __empty(cls) -> AckPdu:
        empty_conf = PduConfig.empty()
        return cls(
            # Still set valid directive code, otherwise ctor will explode
            directive_code_of_acked_pdu=DirectiveType.FINISHED_PDU,
            condition_code_of_acked_pdu=ConditionCode.NO_ERROR,
            transaction_status=TransactionStatus.UNDEFINED,
            pdu_conf=empty_conf,
        )

    def pack(self) -> bytearray:
        packet = self.pdu_file_directive.pack()
        packet.append(
            (self.directive_code_of_acked_pdu << 4) | self.directive_subtype_code
        )
        packet.append((self.condition_code_of_acked_pdu << 4) | self.transaction_status)
        return packet

    @classmethod
    def unpack(cls, data: bytes) -> AckPdu:
        """
        :param data:
        :raise BytesTooShortError:
        :return:
        """
        ack_packet = cls.__empty()
        ack_packet.pdu_file_directive = FileDirectivePduBase.unpack(raw_packet=data)
        current_idx = ack_packet.pdu_file_directive.header_len
        ack_packet.directive_code_of_acked_pdu = (data[current_idx] & 0xF0) >> 4
        ack_packet.directive_subtype_code = data[current_idx] & 0x0F
        current_idx += 1
        ack_packet.condition_code_of_acked_pdu = (data[current_idx] & 0xF0) >> 4
        ack_packet.transaction_status = data[current_idx] & 0x03
        return ack_packet
