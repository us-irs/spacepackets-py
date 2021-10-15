from __future__ import annotations
import enum

from spacepackets.cfdp.pdu.file_directive import FileDirectivePduBase, DirectiveCodes
from spacepackets.cfdp.conf import PduConfig
from spacepackets.cfdp.pdu import IsFileDirective
from spacepackets.log import get_console_logger


class ResponseRequired(enum.IntEnum):
    NAK = 0
    KEEP_ALIVE = 1


class PromptPdu(IsFileDirective):
    """Encapsulates the Prompt file directive PDU, see CCSDS 727.0-B-5 p.84"""

    def __init__(
        self,
        reponse_required: ResponseRequired,
        pdu_conf: PduConfig
    ):
        self.pdu_file_directive = FileDirectivePduBase(
            directive_code=DirectiveCodes.PROMPT_PDU,
            pdu_conf=pdu_conf,
            directive_param_field_len=1
        )
        IsFileDirective.__init__(self, pdu_file_directive=self.pdu_file_directive)
        self.response_required = reponse_required

    @classmethod
    def __empty(cls) -> PromptPdu:
        empty_conf = PduConfig.empty()
        return cls(
            reponse_required=ResponseRequired.NAK,
            pdu_conf=empty_conf
        )

    def pack(self) -> bytearray:
        prompt_pdu = self.pdu_file_directive.pack()
        prompt_pdu.append(self.response_required << 7)
        return prompt_pdu

    @classmethod
    def unpack(cls, raw_packet: bytearray) -> PromptPdu:
        prompt_pdu = cls.__empty()
        prompt_pdu.pdu_file_directive = FileDirectivePduBase.unpack(raw_packet=raw_packet)
        current_idx = prompt_pdu.pdu_file_directive.header_len
        if current_idx >= len(raw_packet):
            logger = get_console_logger()
            logger.warning('Packet length too short')
            raise ValueError
        prompt_pdu.response_required = ResponseRequired((raw_packet[current_idx] & 0x80) >> 7)
        return prompt_pdu
