from unittest import TestCase

from spacepackets.cfdp import CfdpLv, TransactionId
from spacepackets.cfdp.tlv import (
    ProxyPutRequest,
    ProxyPutRequestParams,
    OriginatingTransactionId,
    ORIGINATING_TRANSACTION_ID_MSG_TYPE_ID,
    ProxyMessageType,
    TlvType,
)
from spacepackets.util import ByteFieldU8, ByteFieldU16


class TestReservedMsg(TestCase):
    def setUp(self) -> None:
        self.dest_entity_id = ByteFieldU8(5)
        self.src_string = "hello.txt"
        self.src_name = CfdpLv.from_str(self.src_string)
        self.dest_string = "hello2.txt"
        self.dest_name = CfdpLv.from_str(self.dest_string)
        self.proxy_put_req_params = ProxyPutRequestParams(
            self.dest_entity_id, self.src_name, self.dest_name
        )
        self.proxy_put_request = ProxyPutRequest(self.proxy_put_req_params)
        self.originating_id_source_id = ByteFieldU16(1)
        self.originating_id_seq_num = ByteFieldU16(5)
        self.originating_transaction_id = OriginatingTransactionId(
            TransactionId(self.originating_id_source_id, self.originating_id_seq_num)
        )

    def _generic_raw_data_verification(
        self, data: bytes, expected_custom_len: int, expected_msg_type: int
    ):
        self.assertEqual(data[0], TlvType.MESSAGE_TO_USER)
        # Lenght must hold at least "cfdp" string and message type.
        self.assertTrue(data[1] > 5)
        self.assertEqual(data[1], 5 + expected_custom_len)
        self.assertEqual(data[2:6].decode(), "cfdp")
        self.assertEqual(data[6], expected_msg_type)

    def test_proxy_put_request_state(self):
        self.assertTrue(self.proxy_put_request.is_cfdp_proxy_operation())
        self.assertFalse(self.proxy_put_request.is_directory_operation())
        self.assertFalse(self.proxy_put_request.is_originating_transaction_id())

    def test_proxy_put_req(self):
        self.assertEqual(
            self.proxy_put_request.get_proxy_put_request_params(),
            self.proxy_put_req_params,
        )
        self.assertEqual(
            self.proxy_put_request.get_reserved_cfdp_message_type(),
            ProxyMessageType.PUT_REQUEST,
        )
        self.assertEqual(
            self.proxy_put_request.get_cfdp_proxy_message_type(),
            ProxyMessageType.PUT_REQUEST,
        )
        raw = self.proxy_put_request.pack()
        self._generic_raw_data_verification(
            raw,
            # 2 bytes dest ID LV, and source and dest path LV.
            2 + 1 + len(self.src_string) + 1 + len(self.dest_string),
            ProxyMessageType.PUT_REQUEST,
        )

    def test_conversion_to_generic(self):
        msg_to_user = self.proxy_put_request.to_generic_msg_to_user_tlv()
        self.assertEqual(msg_to_user.tlv_type, TlvType.MESSAGE_TO_USER)

    def test_to_generic_and_to_reserved_again(self):
        msg_to_user = self.proxy_put_request.to_generic_msg_to_user_tlv()
        reserved_msg = msg_to_user.to_reserved_msg_tlv()
        self.assertIsNotNone(reserved_msg)
        self.assertEqual(self.proxy_put_request, reserved_msg)
        self.assertEqual(self.proxy_put_request.packet_len, reserved_msg.packet_len)

    def test_originating_transaction_id_state(self):
        self.assertTrue(self.originating_transaction_id.is_originating_transaction_id())
        self.assertFalse(self.originating_transaction_id.is_cfdp_proxy_operation())
        self.assertFalse(self.originating_transaction_id.is_directory_operation())

    def test_originating_transaction_id_pack(self):
        raw_originating_id = self.originating_transaction_id.pack()
        self._generic_raw_data_verification(
            raw_originating_id, 1 + 2 + 2, ORIGINATING_TRANSACTION_ID_MSG_TYPE_ID
        )
