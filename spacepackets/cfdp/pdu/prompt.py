from __future__ import annotations
import enum

from spacepackets.cfdp.pdu.file_directive import FileDirectivePduBase, DirectiveCodes, Direction, \
    TransmissionModes, CrcFlag


class ResponseRequired(enum.IntEnum):
    NAK = 0
    KEEP_ALIVE = 1


class PromptPdu:
    """Encapsulates the Prompt file directive PDU, see CCSDS 727.0-B-5 p.84"""

    def __init__(
        self,
        reponse_required: ResponseRequired,
        # PDU file directive arguments
        trans_mode: TransmissionModes,
        transaction_seq_num: bytes,
        direction: Direction = Direction.TOWARDS_RECEIVER,
        source_entity_id: bytes = bytes(),
        dest_entity_id: bytes = bytes(),
        crc_flag: CrcFlag = CrcFlag.GLOBAL_CONFIG,
    ):
        self.pdu_file_directive = FileDirectivePduBase(
            directive_code=DirectiveCodes.PROMPT_PDU,
            direction=direction,
            trans_mode=trans_mode,
            crc_flag=crc_flag,
            transaction_seq_num=transaction_seq_num,
            source_entity_id=source_entity_id,
            dest_entity_id=dest_entity_id,
        )
        self.response_required = reponse_required

    @classmethod
    def __empty(cls) -> PromptPdu:
        return cls(
            reponse_required=ResponseRequired.NAK,
            trans_mode=TransmissionModes.UNACKNOWLEDGED,
            transaction_seq_num=bytes([0]),
        )

    def pack(self) -> bytearray:
        prompt_pdu = self.pdu_file_directive.pack()
        prompt_pdu.append(self.response_required << 7)
        return prompt_pdu

    @classmethod
    def unpack(cls, raw_packet: bytearray) -> PromptPdu:
        prompt_pdu = cls.__empty()
        prompt_pdu.pdu_file_directive = FileDirectivePduBase.unpack(raw_packet=raw_packet)
        current_idx = prompt_pdu.pdu_file_directive.get_packet_len()
        prompt_pdu.response_required = raw_packet[current_idx] & 0x80
        return prompt_pdu
