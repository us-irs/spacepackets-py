from __future__ import annotations

from typing import Any, NoReturn, Union, cast

import deprecation

from spacepackets.cfdp.defs import PduType
from spacepackets.cfdp.pdu import (
    AbstractFileDirectiveBase,
    DirectiveType,
)
from spacepackets.cfdp.pdu.ack import AckPdu
from spacepackets.cfdp.pdu.eof import EofPdu
from spacepackets.cfdp.pdu.file_data import FileDataPdu
from spacepackets.cfdp.pdu.finished import FinishedPdu
from spacepackets.cfdp.pdu.header import AbstractPduBase
from spacepackets.cfdp.pdu.keep_alive import KeepAlivePdu
from spacepackets.cfdp.pdu.metadata import MetadataPdu
from spacepackets.cfdp.pdu.nak import NakPdu
from spacepackets.cfdp.pdu.prompt import PromptPdu
from spacepackets.version import get_version

GenericPduPacket = Union[AbstractFileDirectiveBase, AbstractPduBase]


class PduHolder:
    """Helper type to store arbitrary PDU types and cast them to a concrete PDU type conveniently"""

    def __init__(self, pdu: GenericPduPacket | None):
        self.pdu = pdu

    def pack(self) -> bytearray:
        if self.base is None:
            return bytearray()
        return self.base.pack()

    @property
    @deprecation.deprecated(
        deprecated_in="0.19.0",
        current_version=get_version(),
        details="use packet member instead",
    )
    def base(self) -> GenericPduPacket | None:
        return self.pdu

    @base.setter
    @deprecation.deprecated(
        deprecated_in="0.19.0",
        current_version=get_version(),
        details="use packet member instead",
    )
    def base(self, base: GenericPduPacket) -> None:
        self.pdu = base

    @property
    def packet_len(self) -> int:
        if self.pdu is None:
            return 0
        return self.pdu.packet_len

    @property
    def pdu_type(self) -> PduType:
        assert self.pdu is not None
        return self.pdu.pdu_type

    @property
    def is_file_directive(self) -> bool:
        return self.pdu_type == PduType.FILE_DIRECTIVE

    @property
    def pdu_directive_type(self) -> DirectiveType | None:
        """If the contained type is not a PDU file directive, returns None. Otherwise, returns
        the directive type
        """
        if not self.is_file_directive:
            return None
        directive_base = cast("AbstractFileDirectiveBase", self.pdu)
        return directive_base.directive_type

    def __repr__(self):
        return f"{self.__class__.__name__}(base={self.pdu!r}"

    def _raise_not_target_exception(self, pdu_type: type[Any]) -> NoReturn:
        raise TypeError(f"Stored PDU is not {pdu_type.__name__!r}: {self.pdu!r}")

    def _cast_to_concrete_file_directive(self, pdu_type: type[Any], dir_type: DirectiveType) -> Any:  # noqa: ANN401
        if (
            isinstance(self.pdu, AbstractFileDirectiveBase)
            and self.pdu.pdu_type == PduType.FILE_DIRECTIVE  # type: ignore
        ):
            pdu_base = cast("AbstractFileDirectiveBase", self.pdu)
            if pdu_base.directive_type == dir_type and isinstance(self.pdu, pdu_type):
                return self.pdu
        self._raise_not_target_exception(pdu_type)
        return None

    def to_file_data_pdu(self) -> FileDataPdu:  # type: ignore
        if isinstance(self.pdu, AbstractPduBase) and self.pdu.pdu_type == PduType.FILE_DATA:
            return cast("FileDataPdu", self.pdu)
        self._raise_not_target_exception(FileDataPdu)
        return None

    def to_metadata_pdu(self) -> MetadataPdu:
        return self._cast_to_concrete_file_directive(MetadataPdu, DirectiveType.METADATA_PDU)

    def to_ack_pdu(self) -> AckPdu:
        return self._cast_to_concrete_file_directive(AckPdu, DirectiveType.ACK_PDU)

    def to_nak_pdu(self) -> NakPdu:
        return self._cast_to_concrete_file_directive(NakPdu, DirectiveType.NAK_PDU)

    def to_finished_pdu(self) -> FinishedPdu:
        return self._cast_to_concrete_file_directive(FinishedPdu, DirectiveType.FINISHED_PDU)

    def to_eof_pdu(self) -> EofPdu:
        return self._cast_to_concrete_file_directive(EofPdu, DirectiveType.EOF_PDU)

    def to_keep_alive_pdu(self) -> KeepAlivePdu:
        return self._cast_to_concrete_file_directive(KeepAlivePdu, DirectiveType.KEEP_ALIVE_PDU)

    def to_prompt_pdu(self) -> PromptPdu:
        return self._cast_to_concrete_file_directive(PromptPdu, DirectiveType.PROMPT_PDU)


class PduFactory:
    """Helper class to generate PDUs and retrieve PDU information from a raw bytestream"""

    @staticmethod
    def from_raw(data: bytes | bytearray) -> GenericPduPacket | None:  # noqa: PLR0911
        if len(data) == 0:
            return None
        if not PduFactory.is_file_directive(data):
            return FileDataPdu.unpack(data)
        directive = PduFactory.pdu_directive_type(data)
        if directive == DirectiveType.EOF_PDU:
            return EofPdu.unpack(data)
        if directive == DirectiveType.METADATA_PDU:
            return MetadataPdu.unpack(data)
        if directive == DirectiveType.FINISHED_PDU:
            return FinishedPdu.unpack(data)
        if directive == DirectiveType.ACK_PDU:
            return AckPdu.unpack(data)
        if directive == DirectiveType.NAK_PDU:
            return NakPdu.unpack(data)
        if directive == DirectiveType.KEEP_ALIVE_PDU:
            return KeepAlivePdu.unpack(data)
        if directive == DirectiveType.PROMPT_PDU:
            return PromptPdu.unpack(data)
        return None

    @staticmethod
    def from_raw_to_holder(data: bytes | bytearray) -> PduHolder:
        return PduHolder(PduFactory.from_raw(data))

    @staticmethod
    def pdu_type(data: bytes | bytearray) -> PduType:
        return PduType((data[0] >> 4) & 0x01)

    @staticmethod
    def is_file_directive(data: bytes | bytearray) -> bool:
        return PduFactory.pdu_type(data) == PduType.FILE_DIRECTIVE

    @staticmethod
    def pdu_directive_type(data: bytes | bytearray) -> DirectiveType | None:
        """Retrieve the PDU directive type from a raw bytestream.

        :raises ValueError: Invalid directive type.
        :returns: None, if the PDU in the given bytestream is not a file directive, otherwise the
            directive.
        """
        if not PduFactory.is_file_directive(data):
            return None
        header_len = AbstractPduBase.header_len_from_raw(data)
        return DirectiveType(data[header_len])
