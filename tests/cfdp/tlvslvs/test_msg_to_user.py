from unittest import TestCase

from spacepackets.cfdp import MessageToUserTlv, TlvHolder, TlvTypes, TlvTypeMissmatch
from spacepackets.cfdp.tlv import create_cfdp_proxy_and_dir_op_message_marker


class TestMsgToUser(TestCase):
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
