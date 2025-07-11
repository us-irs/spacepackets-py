from __future__ import annotations

import copy
import enum
import struct
from typing import TYPE_CHECKING

import fastcrc

from spacepackets.cfdp.conf import PduConfig
from spacepackets.cfdp.defs import ConditionCode, CrcFlag, Direction
from spacepackets.cfdp.pdu.file_directive import (
    AbstractFileDirectiveBase,
    DirectiveType,
    FileDirectivePduBase,
)

if TYPE_CHECKING:
    from spacepackets.cfdp.pdu.header import PduHeader


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
        pdu_conf: PduConfig,
        directive_code_of_acked_pdu: DirectiveType,
        condition_code_of_acked_pdu: ConditionCode,
        transaction_status: TransactionStatus,
    ):
        """Construct a ACK PDU object

        :param directive_code_of_acked_pdu:
        :param condition_code_of_acked_pdu:
        :param transaction_status:
        :param pdu_conf: PDU configuration parameters
        :raises ValueError: Directive code invalid. Only EOF and Finished PDUs can be acknowledged
        """
        pdu_conf = copy.copy(pdu_conf)
        if directive_code_of_acked_pdu not in [
            DirectiveType.FINISHED_PDU,
            DirectiveType.EOF_PDU,
        ]:
            raise ValueError(f"invalid directive code of acked PDU {directive_code_of_acked_pdu}")
        self.directive_code_of_acked_pdu = directive_code_of_acked_pdu
        self.directive_subtype_code = 0
        if self.directive_code_of_acked_pdu == DirectiveType.FINISHED_PDU:
            pdu_conf.direction = Direction.TOWARDS_RECEIVER
            self.directive_subtype_code = 0b0001
        else:
            pdu_conf.direction = Direction.TOWARDS_SENDER
            self.directive_subtype_code = 0b0000
        self.pdu_file_directive = FileDirectivePduBase(
            directive_code=DirectiveType.ACK_PDU,
            directive_param_field_len=2,
            pdu_conf=pdu_conf,
        )
        self.condition_code_of_acked_pdu = condition_code_of_acked_pdu
        self.transaction_status = transaction_status
        self._calculate_directive_field_len()

    @property
    def directive_type(self) -> DirectiveType:
        return DirectiveType.ACK_PDU

    @property
    def pdu_header(self) -> PduHeader:
        return self.pdu_file_directive.pdu_header

    def __eq__(self, other: object):
        if not isinstance(other, AckPdu):
            return False
        return (
            self.pdu_file_directive == other.pdu_file_directive
            and self.directive_code_of_acked_pdu == other.directive_code_of_acked_pdu
            and self.directive_subtype_code == other.directive_subtype_code
            and self.condition_code_of_acked_pdu == other.condition_code_of_acked_pdu
            and self.transaction_status == other.transaction_status
        )

    def __hash__(self) -> int:
        return hash(
            (
                self.pdu_file_directive,
                self.directive_code_of_acked_pdu,
                self.directive_subtype_code,
                self.condition_code_of_acked_pdu,
                self.transaction_status,
            )
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
        packet.append((self.directive_code_of_acked_pdu << 4) | self.directive_subtype_code)
        packet.append((self.condition_code_of_acked_pdu << 4) | self.transaction_status)
        if self.pdu_file_directive.pdu_conf.crc_flag == CrcFlag.WITH_CRC:
            packet.extend(struct.pack("!H", fastcrc.crc16.ibm_3740(bytes(packet))))
        return packet

    def _calculate_directive_field_len(self) -> None:
        directive_param_field_len = 2
        if self.pdu_file_directive.pdu_conf.crc_flag == CrcFlag.WITH_CRC:
            directive_param_field_len += 2
        self.pdu_file_directive.directive_param_field_len = directive_param_field_len

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(pdu_conf={self.pdu_file_directive.pdu_conf!r}, "
            f"directive_code_of_acked_pdu={self.directive_code_of_acked_pdu!r}, "
            f"condition_code_of_acked_pdu={self.condition_code_of_acked_pdu!r}, "
            f"transaction_status={self.transaction_status!r})"
        )

    @classmethod
    def unpack(cls, data: bytes | bytearray) -> AckPdu:
        """Generate an object instance from raw data. Care should be taken to check whether
        the raw bytestream really contains an ACK PDU.

        Raises
        --------

        BytesTooShortError
            Raw data too short for expected object.
        ValueError
            Invalid directive type or data format.
        InvalidCrcError
            PDU has a 16 bit CRC and the CRC check failed.

        """
        ack_packet = cls.__empty()
        ack_packet.pdu_file_directive = FileDirectivePduBase.unpack(raw_packet=data)
        ack_packet.pdu_file_directive.verify_length_and_checksum(data)
        current_idx = ack_packet.pdu_file_directive.header_len
        ack_packet.directive_code_of_acked_pdu = (data[current_idx] & 0xF0) >> 4
        ack_packet.directive_subtype_code = data[current_idx] & 0x0F
        current_idx += 1
        ack_packet.condition_code_of_acked_pdu = (data[current_idx] & 0xF0) >> 4
        ack_packet.transaction_status = data[current_idx] & 0x03
        return ack_packet
