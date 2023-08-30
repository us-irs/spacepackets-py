from unittest import TestCase

from spacepackets.cfdp import CfdpLv
from spacepackets.cfdp.tlv import (
    ProxyPutRequest,
    ProxyPutRequestParams,
    ProxyMessageType,
    TlvType,
)
from spacepackets.util import ByteFieldU8


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

    def test_reserved_cfdp_msg(self):
        self.assertEqual(
            self.proxy_put_request.get_proxy_put_request_params(),
            self.proxy_put_req_params,
        )
        self.assertEqual(
            self.proxy_put_request.get_reserved_cfdp_message_type(),
            ProxyMessageType.PUT_REQUEST,
        )
        self.assertEqual(self.proxy_put_request.is_cfdp_proxy_operation(), True)
        self.assertEqual(
            self.proxy_put_request.get_cfdp_proxy_message_type(),
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
