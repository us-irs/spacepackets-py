from __future__ import annotations
import enum
import struct

from spacepackets.cfdp import CrcFlag
from spacepackets.cfdp.pdu.file_directive import FileDirectivePduBase, DirectiveType
from spacepackets.cfdp.conf import PduConfig
from spacepackets.cfdp.pdu import AbstractFileDirectiveBase, PduHeader
from spacepackets.crc import CRC16_CCITT_FUNC
from spacepackets.exceptions import BytesTooShortError


class ResponseRequired(enum.IntEnum):
    NAK = 0
    KEEP_ALIVE = 1


class PromptPdu(AbstractFileDirectiveBase):
    """Encapsulates the Prompt file directive PDU, see CCSDS 727.0-B-5 p.84"""

    def __init__(self, pdu_conf: PduConfig, response_required: ResponseRequired):
        self.pdu_file_directive = FileDirectivePduBase(
            directive_code=DirectiveType.PROMPT_PDU,
            pdu_conf=pdu_conf,
            directive_param_field_len=1,
        )
        if pdu_conf.crc_flag == CrcFlag.WITH_CRC:
            self.pdu_file_directive.directive_param_field_len = 3
        self.response_required = response_required

    @property
    def directive_type(self) -> DirectiveType:
        return self.pdu_file_directive.directive_type

    @property
    def pdu_header(self) -> PduHeader:
        return self.pdu_file_directive.pdu_header

    @classmethod
    def __empty(cls) -> PromptPdu:
        empty_conf = PduConfig.empty()
        return cls(response_required=ResponseRequired.NAK, pdu_conf=empty_conf)

    def pack(self) -> bytearray:
        prompt_pdu = self.pdu_file_directive.pack()
        prompt_pdu.append(self.response_required << 7)
        if self.pdu_file_directive.pdu_conf.crc_flag == CrcFlag.WITH_CRC:
            prompt_pdu.extend(struct.pack("!H", CRC16_CCITT_FUNC(prompt_pdu)))
        return prompt_pdu

    @classmethod
    def unpack(cls, data: bytes) -> PromptPdu:
        """
        :param data:
        :raises BytesTooShortError:
        :return:
        """
        prompt_pdu = cls.__empty()
        prompt_pdu.pdu_file_directive = FileDirectivePduBase.unpack(raw_packet=data)
        prompt_pdu.pdu_file_directive.verify_length_and_checksum(data)
        current_idx = prompt_pdu.pdu_file_directive.header_len
        if current_idx >= len(data):
            raise BytesTooShortError(current_idx, len(data))
        prompt_pdu.response_required = ResponseRequired((data[current_idx] & 0x80) >> 7)
        return prompt_pdu

    def __eq__(self, other: PromptPdu):
        return (
            self.pdu_file_directive == other.pdu_file_directive
            and self.response_required == other.response_required
        )
