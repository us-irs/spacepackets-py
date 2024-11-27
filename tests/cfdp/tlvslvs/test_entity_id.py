from unittest import TestCase

from spacepackets.cfdp import (
    CfdpTlv,
    EntityIdTlv,
    TlvHolder,
    TlvType,
    TlvTypeMissmatchError,
)


class TestEntityIdTlvs(TestCase):
    def setUp(self) -> None:
        self.entity_id_tlv = EntityIdTlv(entity_id=bytes([0x00, 0x01, 0x02, 0x03]))
        self.cfdp_tlv = CfdpTlv(
            tlv_type=self.entity_id_tlv.tlv_type, value=self.entity_id_tlv.value
        )

    def test_entity_id_tlv(self):
        self.assertEqual(self.entity_id_tlv.tlv_type, TlvType.ENTITY_ID)
        self.assertEqual(self.entity_id_tlv.packet_len, 6)
        self.assertEqual(self.entity_id_tlv.value, bytes([0x00, 0x01, 0x02, 0x03]))

    def test_holder(self):
        wrapper = TlvHolder(self.entity_id_tlv)
        self.assertEqual(wrapper.tlv_type, TlvType.ENTITY_ID)
        entity_id_tlv_from_factory = wrapper.to_entity_id()
        self.assertEqual(entity_id_tlv_from_factory, self.entity_id_tlv)

    def test_holder_cfdp_tlv(self):
        holder = TlvHolder(self.cfdp_tlv)
        entity_id_tlv = holder.to_entity_id()
        self.assertEqual(self.entity_id_tlv, entity_id_tlv)

    def test_from_cfdp_tlv(self):
        entity_id = EntityIdTlv.from_tlv(self.cfdp_tlv)
        self.assertEqual(entity_id, self.entity_id_tlv)

    def test_invalid_type(self):
        entity_id_tlv_tlv = self.entity_id_tlv.tlv
        entity_id_tlv_tlv.tlv_type = TlvType.FILESTORE_REQUEST
        with self.assertRaises(TlvTypeMissmatchError):
            EntityIdTlv.from_tlv(cfdp_tlv=entity_id_tlv_tlv)

    def test_custom_eq(self):
        self.entity_id_tlv = EntityIdTlv(entity_id=bytes([0x00, 0x01]))
        self.entity_id_tlv_same = EntityIdTlv(entity_id=bytes([0x01]))
        self.assertEqual(self.entity_id_tlv, self.entity_id_tlv_same)

    def test_repr(self):
        repr_str = repr(self.entity_id_tlv)
        self.assertEqual(repr_str, f"Tlv(tlv_type={TlvType.ENTITY_ID!r}, value=0x[00,01,02,03])")
