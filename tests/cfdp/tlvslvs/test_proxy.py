from unittest import TestCase

from spacepackets.cfdp import CfdpLv
from spacepackets.cfdp.tlv import ProxyPutRequest, TlvType
from spacepackets.util import ByteFieldU8


class TestProxyPacket(TestCase):
    def test_basic(self):
        dest_entity_id = ByteFieldU8(5)
        src_name = CfdpLv.from_str("hello.txt")
        dest_name = CfdpLv.from_str("hello2.txt")
        proxy_put_req = ProxyPutRequest(dest_entity_id, src_name, dest_name)
        self.assertEqual(proxy_put_req.tlv_type, TlvType.MESSAGE_TO_USER)
        self.assertEqual(
            proxy_put_req.packet_len,
            2
            + 1
            + dest_entity_id.byte_len
            + 1
            + src_name.packet_len
            + dest_name.packet_len,
        )
        pass
