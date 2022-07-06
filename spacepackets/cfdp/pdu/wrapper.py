from typing import cast, Union, Type

from spacepackets.cfdp import PduType
from spacepackets.cfdp.pdu import (
    MetadataPdu,
    AbstractFileDirectiveBase,
    DirectiveType,
    AckPdu,
    NakPdu,
    FinishedPdu,
    EofPdu,
    KeepAlivePdu,
    PromptPdu,
)
from spacepackets.cfdp.pdu.file_data import FileDataPdu
from spacepackets.cfdp.pdu.header import AbstractPduBase


class PduWrapper:
    """Helper type to store arbitrary PDU types and cast them to a concrete PDU type conveniently"""

    def __init__(self, base: Union[AbstractFileDirectiveBase, AbstractPduBase]):
        self.base = base

    def _raise_not_target_exception(self, pdu_type: Type[any]):
        raise TypeError(
            f"Stored PDU is not {pdu_type.__class__.__name__}: {self.base!r}"
        )

    def _cast_to_concrete_file_directive(
        self, pdu_type: Type[any], dir_type: DirectiveType
    ):
        if (
            isinstance(self.base, AbstractFileDirectiveBase)
            and self.base.pdu_type == PduType.FILE_DIRECTIVE
        ):
            pdu_base = cast(AbstractFileDirectiveBase, self.base)
            if pdu_base.directive_type == dir_type:
                return cast(pdu_type, self.base)
        self._raise_not_target_exception(pdu_type)

    def to_file_data_pdu(self) -> FileDataPdu:
        if (
            isinstance(self.base, AbstractPduBase)
            and self.base.pdu_type == PduType.FILE_DATA
        ):
            return cast(FileDataPdu, self.base)
        else:
            self._raise_not_target_exception(FileDataPdu)

    def to_metadata_pdu(self) -> MetadataPdu:
        return self._cast_to_concrete_file_directive(
            MetadataPdu, DirectiveType.METADATA_PDU
        )

    def to_ack_pdu(self) -> AckPdu:
        return self._cast_to_concrete_file_directive(AckPdu, DirectiveType.ACK_PDU)

    def to_nak_pdu(self) -> NakPdu:
        return self._cast_to_concrete_file_directive(NakPdu, DirectiveType.NAK_PDU)

    def to_finished_pdu(self) -> FinishedPdu:
        return self._cast_to_concrete_file_directive(
            FinishedPdu, DirectiveType.FINISHED_PDU
        )

    def to_eof_pdu(self) -> EofPdu:
        return self._cast_to_concrete_file_directive(EofPdu, DirectiveType.EOF_PDU)

    def to_keep_alive_pdu(self) -> KeepAlivePdu:
        return self._cast_to_concrete_file_directive(
            KeepAlivePdu, DirectiveType.KEEP_ALIVE_PDU
        )

    def to_prompt_pdu(self) -> PromptPdu:
        return self._cast_to_concrete_file_directive(
            PromptPdu, DirectiveType.PROMPT_PDU
        )
