from unittest import TestCase

from spacepackets.cfdp import (
    FaultHandlerOverrideTlv,
    ConditionCode,
    FaultHandlerCode,
    TlvHolder,
    TlvTypes,
    TlvTypeMissmatch,
    CfdpTlv,
)


class TestFaultHandlerOverrideTlv(TestCase):
    def setUp(self) -> None:
        self.fault_handler_ovvrd_tlv = FaultHandlerOverrideTlv(
            condition_code=ConditionCode.POSITIVE_ACK_LIMIT_REACHED,
            handler_code=FaultHandlerCode.IGNORE_ERROR,
        )
        self.cfdp_tlv = CfdpTlv(
            self.fault_handler_ovvrd_tlv.tlv_type, self.fault_handler_ovvrd_tlv.value
        )

    def test_holder(self):
        holder = TlvHolder(self.fault_handler_ovvrd_tlv)
        fault_handler_ovvrd_tlv_from_fac = holder.to_fault_handler_override()
        self.assertEqual(fault_handler_ovvrd_tlv_from_fac, self.fault_handler_ovvrd_tlv)

    def test_from_cfdp_tlv(self):
        self.assertEqual(
            TlvHolder(self.cfdp_tlv).to_fault_handler_override(),
            self.fault_handler_ovvrd_tlv,
        )

    def test_type_missmatch(self):
        fault_handler_ovvrd_tlv_tlv = self.fault_handler_ovvrd_tlv.tlv
        fault_handler_ovvrd_tlv_tlv.tlv_type = TlvTypes.ENTITY_ID
        with self.assertRaises(TlvTypeMissmatch):
            FaultHandlerOverrideTlv.from_tlv(cfdp_tlv=fault_handler_ovvrd_tlv_tlv)

    def test_unpack(self):
        raw = self.fault_handler_ovvrd_tlv.pack()
        unpacked = FaultHandlerOverrideTlv.unpack(raw)
        self.assertEqual(unpacked, self.fault_handler_ovvrd_tlv)
