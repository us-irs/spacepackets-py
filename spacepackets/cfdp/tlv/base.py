from __future__ import annotations
from typing import List
from abc import ABC, abstractmethod
from spacepackets.cfdp.exceptions import TlvTypeMissmatch
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

    def __eq__(self, other: AbstractTlvBase):
        return self.tlv_type == other.tlv_type and self.value == other.value

    def check_type(self, tlv_type: TlvType):
        if self.tlv_type != tlv_type:
            raise TlvTypeMissmatch(found=tlv_type, expected=self.tlv_type)


TlvList = List[AbstractTlvBase]
