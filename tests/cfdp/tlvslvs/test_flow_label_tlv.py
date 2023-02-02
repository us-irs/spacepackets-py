from unittest import TestCase

from spacepackets.cfdp import (
    TlvTypes,
    TlvHolder,
    TlvTypeMissmatch,
)
from spacepackets.cfdp.tlv import (
    FlowLabelTlv,
    CfdpTlv,
)


class TestFlowLabelTlvs(TestCase):
    def setUp(self) -> None:
        self.flow_label_tlv = FlowLabelTlv(flow_label=bytes([0x00]))
        self.cfdp_tlv = CfdpTlv(
            tlv_type=self.flow_label_tlv.tlv_type, value=self.flow_label_tlv.value
        )

    def test_basic(self):
        self.assertEqual(self.flow_label_tlv.value, bytes([0x00]))

    def test_holder(self):
        wrapper = TlvHolder(self.flow_label_tlv)
        flow_label_tlv_from_fac = wrapper.to_flow_label()
        self.assertEqual(flow_label_tlv_from_fac, self.flow_label_tlv)

    def test_from_cfdp_tlv(self):
        holder = TlvHolder(self.cfdp_tlv)
        flow_label_tlv = holder.to_flow_label()
        self.assertEqual(self.flow_label_tlv, flow_label_tlv)

    def test_flow_label_tlv(self):
        flow_label_tlv_tlv = self.flow_label_tlv.tlv
        flow_label_tlv_raw = self.flow_label_tlv.pack()
        flow_label_tlv_unpacked = FlowLabelTlv.unpack(data=flow_label_tlv_raw)
        self.assertEqual(flow_label_tlv_unpacked.tlv.value, bytes([0x00]))
        flow_label_tlv_tlv.tlv_type = TlvTypes.FILESTORE_REQUEST
        with self.assertRaises(TlvTypeMissmatch):
            FlowLabelTlv.from_tlv(cfdp_tlv=flow_label_tlv_tlv)
        flow_label_tlv_raw[0] = TlvTypes.FILESTORE_REQUEST
        with self.assertRaises(TlvTypeMissmatch):
            FlowLabelTlv.unpack(data=flow_label_tlv_raw)
