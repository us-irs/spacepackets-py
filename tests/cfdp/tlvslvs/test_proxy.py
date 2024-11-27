from unittest import TestCase

from spacepackets.cfdp import CfdpLv
from spacepackets.cfdp.tlv import (
    ProxyMessageType,
    ProxyPutRequest,
    ProxyPutRequestParams,
    TlvType,
)
from spacepackets.util import ByteFieldU8


class TestProxyPacket(TestCase):
    def setUp(self) -> None:
        self.dest_entity_id = ByteFieldU8(5)
        self.src_string = "hello.txt"
        self.src_name = CfdpLv.from_str(self.src_string)
        self.dest_string = "hello2.txt"
        self.dest_name = CfdpLv.from_str(self.dest_string)
        proxy_put_req_params = ProxyPutRequestParams(
            self.dest_entity_id, self.src_name, self.dest_name
        )
        self.proxy_put_req = ProxyPutRequest(proxy_put_req_params)
        self.expected_raw_len = (
            2  # TLV header
            + len(b"cfdp")
            + 1  # Message type
            + self.dest_entity_id.byte_len
            + 1
            + self.src_name.packet_len
            + self.dest_name.packet_len
        )

    def test_basic(self):
        self.assertEqual(self.proxy_put_req.tlv_type, TlvType.MESSAGE_TO_USER)
        self.assertEqual(self.proxy_put_req.packet_len, self.expected_raw_len)

    def test_pack(self):
        raw_proxy_put_req = self.proxy_put_req.pack()
        self.assertEqual(len(raw_proxy_put_req), self.expected_raw_len)
        self.assertEqual(raw_proxy_put_req[0], TlvType.MESSAGE_TO_USER)
        self.assertEqual(raw_proxy_put_req[1], self.expected_raw_len - 2)
        self.assertEqual(raw_proxy_put_req[2:6].decode(), "cfdp")
        self.assertEqual(raw_proxy_put_req[6], ProxyMessageType.PUT_REQUEST)
        self.assertEqual(raw_proxy_put_req[7], 1)
        self.assertEqual(raw_proxy_put_req[8], self.dest_entity_id.value)
        self.assertEqual(raw_proxy_put_req[9], len(self.src_string))
        current_idx = 10
        self.assertEqual(
            raw_proxy_put_req[current_idx : current_idx + len(self.src_string)].decode(),
            self.src_string,
        )
        current_idx += len(self.src_string)
        self.assertEqual(raw_proxy_put_req[current_idx], len(self.dest_string))
        current_idx += 1
        self.assertEqual(
            raw_proxy_put_req[current_idx : current_idx + len(self.dest_string)].decode(),
            self.dest_string,
        )
        current_idx += len(self.dest_string)
        self.assertEqual(current_idx, self.expected_raw_len)
