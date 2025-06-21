from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from spacepackets.cfdp.tlv.defs import TlvTypeMissmatchError

if TYPE_CHECKING:
    from spacepackets.cfdp.tlv.defs import TlvType


class AbstractTlvBase(ABC):
    @abstractmethod
    def pack(self) -> bytearray:
        pass

    @property
    @abstractmethod
    def packet_len(self) -> int:
        pass

    @property
    @abstractmethod
    def tlv_type(self) -> TlvType:
        pass

    @property
    @abstractmethod
    def value(self) -> bytes:
        pass

    def __repr__(self) -> str:
        return f"Tlv(tlv_type={self.tlv_type!r}, value=0x[{self.value.hex(sep=',')}])"

    def __eq__(self, other: object):
        if not isinstance(other, AbstractTlvBase):
            return False
        return self.tlv_type == other.tlv_type and self.value == other.value

    def __hash__(self) -> int:
        return hash((self.value, self.tlv_type))

    def check_type(self, tlv_type: TlvType) -> None:
        if self.tlv_type != tlv_type:
            raise TlvTypeMissmatchError(found=tlv_type, expected=self.tlv_type)


TlvList = list[AbstractTlvBase]
