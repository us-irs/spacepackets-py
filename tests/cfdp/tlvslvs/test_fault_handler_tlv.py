from unittest import TestCase

from spacepackets.cfdp import FaultHandlerOverrideTlv, ConditionCode, FaultHandlerCodes, TlvHolder, \
    TlvTypes, TlvTypeMissmatch


class TestFaultHandlerOverrideTlv(TestCase):
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
