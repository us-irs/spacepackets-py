from unittest import TestCase

from spacepackets.cfdp import (
    TlvTypes,
    TlvHolder,
    TlvTypeMissmatch,
)
from spacepackets.cfdp.tlv import (
    FlowLabelTlv,
)


class TestFlowLabelTlvs(TestCase):
    def test_flow_label_tlv(self):
        flow_label_tlv = FlowLabelTlv(flow_label=bytes([0x00]))
        flow_label_tlv_tlv = flow_label_tlv.tlv
        wrapper = TlvHolder(flow_label_tlv)
        flow_label_tlv_from_fac = wrapper.to_flow_label()
        self.assertEqual(flow_label_tlv_from_fac.pack(), flow_label_tlv.pack())
        flow_label_tlv_raw = flow_label_tlv.pack()
        flow_label_tlv_unpacked = FlowLabelTlv.unpack(raw_bytes=flow_label_tlv_raw)
        self.assertEqual(flow_label_tlv_unpacked.tlv.value, bytes([0x00]))
        flow_label_tlv_tlv.tlv_type = TlvTypes.FILESTORE_REQUEST
        with self.assertRaises(TlvTypeMissmatch):
            FlowLabelTlv.from_tlv(cfdp_tlv=flow_label_tlv_tlv)
        flow_label_tlv_raw[0] = TlvTypes.FILESTORE_REQUEST
        with self.assertRaises(TlvTypeMissmatch):
            FlowLabelTlv.unpack(raw_bytes=flow_label_tlv_raw)
