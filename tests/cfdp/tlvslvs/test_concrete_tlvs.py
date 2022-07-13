from unittest import TestCase

from spacepackets.cfdp import (
    TlvTypes,
    ConditionCode,
    FaultHandlerCodes,
    TlvHolder,
    TlvTypeMissmatch,
)
from spacepackets.cfdp.tlv import (
    FaultHandlerOverrideTlv,
    MessageToUserTlv,
    create_cfdp_proxy_and_dir_op_message_marker,
    FlowLabelTlv,
)


class TestConcreteTlvs(TestCase):
    def test_fault_handler_override_tlv(self):
        fault_handler_ovvrd_tlv = FaultHandlerOverrideTlv(
            condition_code=ConditionCode.POSITIVE_ACK_LIMIT_REACHED,
            handler_code=FaultHandlerCodes.IGNORE_ERROR,
        )
        fault_handler_ovvrd_tlv_tlv = fault_handler_ovvrd_tlv.tlv
        wrapper = TlvHolder(fault_handler_ovvrd_tlv)
        fault_handler_ovvrd_tlv_from_fac = wrapper.to_fault_handler_override()
        self.assertEqual(
            fault_handler_ovvrd_tlv_from_fac.pack(), fault_handler_ovvrd_tlv.pack()
        )
        fault_handler_ovvrd_tlv_tlv.tlv_type = TlvTypes.ENTITY_ID
        with self.assertRaises(TlvTypeMissmatch):
            FaultHandlerOverrideTlv.from_tlv(cfdp_tlv=fault_handler_ovvrd_tlv_tlv)

    def test_msg_to_user_tlv(self):
        msg_to_usr_tlv = MessageToUserTlv(msg=bytes([0x00]))
        msg_to_usr_tlv_tlv = msg_to_usr_tlv.tlv
        wrapper = TlvHolder(msg_to_usr_tlv)
        msg_to_usr_tlv_from_fac = wrapper.to_msg_to_user()
        self.assertEqual(msg_to_usr_tlv_from_fac.pack(), msg_to_usr_tlv.pack())
        msg_to_usr_tlv_tlv.tlv_type = TlvTypes.FILESTORE_REQUEST
        with self.assertRaises(TlvTypeMissmatch):
            MessageToUserTlv.from_tlv(cfdp_tlv=msg_to_usr_tlv_tlv)
        msg_to_usr_tlv_tlv.tlv_type = TlvTypes.MESSAGE_TO_USER
        msg_to_usr_tlv_raw = msg_to_usr_tlv.pack()
        msg_to_usr_tlv_unpacked = MessageToUserTlv.unpack(raw_bytes=msg_to_usr_tlv_raw)
        self.assertEqual(msg_to_usr_tlv_unpacked.tlv.value, bytes([0x00]))
        self.assertFalse(msg_to_usr_tlv_unpacked.is_standard_proxy_dir_ops_msg())
        proxy_val = create_cfdp_proxy_and_dir_op_message_marker()
        msg_to_usr_tlv = MessageToUserTlv(msg=proxy_val)
        self.assertTrue(msg_to_usr_tlv.is_standard_proxy_dir_ops_msg())

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
