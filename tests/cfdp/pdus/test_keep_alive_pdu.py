from unittest import TestCase

from spacepackets.cfdp import LargeFileFlag
from spacepackets.cfdp.conf import PduConfig
from spacepackets.cfdp.pdu import KeepAlivePdu, DirectiveType


class TestKeepAlivePdu(TestCase):
    def test_keep_alive_pdu(self):
        pdu_conf = PduConfig.empty()
        keep_alive_pdu = KeepAlivePdu(pdu_conf=pdu_conf, progress=0)
        self.assertEqual(keep_alive_pdu.progress, 0)
        self.assertEqual(keep_alive_pdu.file_flag, LargeFileFlag.NORMAL)
        keep_alive_pdu_raw = keep_alive_pdu.pack()
        self.assertEqual(
            keep_alive_pdu_raw,
            bytes(
                [
                    0x20,
                    0x00,
                    0x05,
                    0x11,
                    0x00,
                    0x00,
                    0x00,
                    DirectiveType.KEEP_ALIVE_PDU,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                ]
            ),
        )
        self.assertEqual(keep_alive_pdu.packet_len, 12)
        keep_alive_unpacked = KeepAlivePdu.unpack(raw_packet=keep_alive_pdu_raw)
        self.assertEqual(keep_alive_unpacked.packet_len, 12)
        self.assertEqual(keep_alive_unpacked.progress, 0)
        keep_alive_pdu.file_flag = LargeFileFlag.LARGE
        self.assertEqual(keep_alive_pdu.packet_len, 16)
        keep_alive_pdu_large = keep_alive_pdu.pack()
        self.assertEqual(len(keep_alive_pdu_large), 16)

        keep_alive_pdu.file_flag = LargeFileFlag.NORMAL
        self.assertEqual(keep_alive_pdu.file_flag, LargeFileFlag.NORMAL)

        keep_alive_pdu.progress = pow(2, 32) + 1
        with self.assertRaises(ValueError):
            keep_alive_pdu.pack()

        pdu_conf.fss_field_len = LargeFileFlag.LARGE
        keep_alive_pdu_large = KeepAlivePdu(pdu_conf=pdu_conf, progress=0)
        keep_alive_pdu_invalid = keep_alive_pdu_large.pack()[:-1]
        with self.assertRaises(ValueError):
            KeepAlivePdu.unpack(raw_packet=keep_alive_pdu_invalid)
