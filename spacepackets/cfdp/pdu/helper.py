from __future__ import annotations
from typing import cast, Union, Type, Optional

from spacepackets.cfdp import PduTypes
from spacepackets.cfdp.pdu import (
    MetadataPdu,
    AbstractFileDirectiveBase,
    DirectiveTypes,
    AckPdu,
    NakPdu,
    FinishedPdu,
    EofPdu,
    KeepAlivePdu,
    PromptPdu,
)
from spacepackets.cfdp.pdu.file_data import FileDataPdu
from spacepackets.cfdp.pdu.header import AbstractPduBase

GenericPduPacket = Union[AbstractFileDirectiveBase, AbstractPduBase]


class PduHolder:
    """Helper type to store arbitrary PDU types and cast them to a concrete PDU type conveniently"""

    def __init__(self, base: Optional[GenericPduPacket]):
        self.base = base

    def pack(self) -> bytearray:
        if self.base is None:
            return bytearray()
        return self.base.pack()

    @property
    def packet_len(self) -> int:
        if self.base is None:
            return 0
        return self.base.packet_len

    @property
    def pdu_type(self) -> PduTypes:
        return self.base.pdu_header.pdu_type

    @property
    def is_file_directive(self):
        return self.pdu_type == PduTypes.FILE_DIRECTIVE

    @property
    def pdu_directive_type(self) -> Optional[DirectiveTypes]:
        """If the contained type is not a PDU file directive, returns None. Otherwise, returns
        the directive type
        """
        if not self.is_file_directive:
            return None
        directive_base = cast(AbstractFileDirectiveBase, self.base)
        return directive_base.directive_type

    def __repr__(self):
        return f"{self.__class__.__name__}(base={self.base!r}"

    def _raise_not_target_exception(self, pdu_type: Type[any]):
        raise TypeError(f"Stored PDU is not {pdu_type.__name__!r}: {self.base!r}")

    def _cast_to_concrete_file_directive(
        self, pdu_type: Type[any], dir_type: DirectiveTypes
    ):
        if (
            isinstance(self.base, AbstractFileDirectiveBase)
            and self.base.pdu_type == PduTypes.FILE_DIRECTIVE
        ):
            pdu_base = cast(AbstractFileDirectiveBase, self.base)
            if pdu_base.directive_type == dir_type:
                return cast(pdu_type, self.base)
        self._raise_not_target_exception(pdu_type)

    def to_file_data_pdu(self) -> FileDataPdu:
        if (
            isinstance(self.base, AbstractPduBase)
            and self.base.pdu_type == PduTypes.FILE_DATA
        ):
            return cast(FileDataPdu, self.base)
        else:
            self._raise_not_target_exception(FileDataPdu)

    def to_metadata_pdu(self) -> MetadataPdu:
        return self._cast_to_concrete_file_directive(
            MetadataPdu, DirectiveTypes.METADATA_PDU
        )

    def to_ack_pdu(self) -> AckPdu:
        return self._cast_to_concrete_file_directive(AckPdu, DirectiveTypes.ACK_PDU)

    def to_nak_pdu(self) -> NakPdu:
        return self._cast_to_concrete_file_directive(NakPdu, DirectiveTypes.NAK_PDU)

    def to_finished_pdu(self) -> FinishedPdu:
        return self._cast_to_concrete_file_directive(
            FinishedPdu, DirectiveTypes.FINISHED_PDU
        )

    def to_eof_pdu(self) -> EofPdu:
        return self._cast_to_concrete_file_directive(EofPdu, DirectiveTypes.EOF_PDU)

    def to_keep_alive_pdu(self) -> KeepAlivePdu:
        return self._cast_to_concrete_file_directive(
            KeepAlivePdu, DirectiveTypes.KEEP_ALIVE_PDU
        )

    def to_prompt_pdu(self) -> PromptPdu:
        return self._cast_to_concrete_file_directive(
            PromptPdu, DirectiveTypes.PROMPT_PDU
        )


class PduFactory:
    """Helper class to generate PDUs and retrieve PDU information from a raw bytestream"""

    @staticmethod
    def from_raw(data: bytes) -> Optional[GenericPduPacket]:
        if not PduFactory.is_file_directive(data):
            return FileDataPdu.unpack(data)
        else:
            directive = PduFactory.pdu_directive_type(data)
            if directive == DirectiveTypes.EOF_PDU:
                return EofPdu.unpack(data)
            elif directive == DirectiveTypes.METADATA_PDU:
                return MetadataPdu.unpack(data)
            elif directive == DirectiveTypes.FINISHED_PDU:
                return FinishedPdu.unpack(data)
            elif directive == DirectiveTypes.ACK_PDU:
                return AckPdu.unpack(data)
            elif directive == DirectiveTypes.NAK_PDU:
                return NakPdu.unpack(data)
            elif directive == DirectiveTypes.KEEP_ALIVE_PDU:
                return KeepAlivePdu.unpack(data)
            elif directive == DirectiveTypes.PROMPT_PDU:
                return PromptPdu.unpack(data)
        return None

    @staticmethod
    def pdu_type(data: bytes) -> PduTypes:
        return PduTypes((data[0] >> 4) & 0x01)

    @staticmethod
    def is_file_directive(data: bytes) -> bool:
        return PduFactory.pdu_type(data) == PduTypes.FILE_DIRECTIVE

    @staticmethod
    def pdu_directive_type(data: bytes) -> Optional[DirectiveTypes]:
        """Retrieve the PDU directive type from a raw bytestream.

        :raises ValueError: Invalid directive type.
        :returns: None, if the PDU in the given bytestream is not a file directive, otherwise the
            directive.
        """
        if not PduFactory.is_file_directive(data):
            return None
        else:
            header_len = AbstractPduBase.header_len_from_raw(data)
            return DirectiveTypes(data[header_len])
