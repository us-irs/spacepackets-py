from __future__ import annotations
from spacepackets.cfdp.tlv.defs import TlvType
from spacepackets.cfdp.tlv.tlv import CfdpTlv
from spacepackets.cfdp.exceptions import TlvTypeMissmatch
from spacepackets.cfdp.tlv.base import AbstractTlvBase


class EntityIdTlv(AbstractTlvBase):
    TLV_TYPE = TlvType.ENTITY_ID

    def __init__(self, entity_id: bytes):
        self.tlv = CfdpTlv(tlv_type=TlvType.ENTITY_ID, value=entity_id)

    def pack(self) -> bytearray:
        return self.tlv.pack()

    @property
    def packet_len(self):
        return self.tlv.packet_len

    @property
    def tlv_type(self) -> TlvType:
        return EntityIdTlv.TLV_TYPE

    @property
    def value(self) -> bytes:
        return self.tlv.value

    @classmethod
    def __empty(cls) -> EntityIdTlv:
        return cls(entity_id=bytes())

    @classmethod
    def unpack(cls, data: bytes) -> EntityIdTlv:
        entity_id_tlv = cls.__empty()
        entity_id_tlv.tlv = CfdpTlv.unpack(data=data)
        entity_id_tlv.check_type(tlv_type=TlvType.ENTITY_ID)
        return entity_id_tlv

    @classmethod
    def from_tlv(cls, cfdp_tlv: CfdpTlv) -> EntityIdTlv:
        if cfdp_tlv.tlv_type != cls.TLV_TYPE:
            raise TlvTypeMissmatch(cfdp_tlv.tlv_type, cls.TLV_TYPE)
        entity_id_tlv = cls.__empty()
        entity_id_tlv.tlv = cfdp_tlv
        return entity_id_tlv
