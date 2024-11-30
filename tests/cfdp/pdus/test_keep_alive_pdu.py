from unittest import TestCase

from spacepackets.cfdp import LargeFileFlag, PduFactory
from spacepackets.cfdp.conf import PduConfig
from spacepackets.cfdp.defs import Direction
from spacepackets.cfdp.pdu import DirectiveType, KeepAlivePdu


class TestKeepAlivePdu(TestCase):
    def setUp(self) -> None:
        self.pdu_conf = PduConfig.default()
        self.keep_alive_pdu = KeepAlivePdu(pdu_conf=self.pdu_conf, progress=0)

    # TODO: Split into smaller fixtures
    def test_keep_alive_pdu(self):
        self.assertEqual(self.keep_alive_pdu.progress, 0)
        self.assertEqual(self.keep_alive_pdu.direction, Direction.TOWARDS_SENDER)
        self.assertEqual(self.keep_alive_pdu.file_flag, LargeFileFlag.NORMAL)
        keep_alive_pdu_raw = self.keep_alive_pdu.pack()
        self.assertEqual(
            keep_alive_pdu_raw,
            bytes(
                [
                    0x28,
                    0x00,
                    0x05,
                    0x00,
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
        self.assertEqual(self.keep_alive_pdu.packet_len, 12)
        self.keep_alive_pdu.file_flag = LargeFileFlag.NORMAL
        self.assertEqual(self.keep_alive_pdu.file_flag, LargeFileFlag.NORMAL)

        self.keep_alive_pdu.progress = pow(2, 32) + 1
        with self.assertRaises(ValueError):
            self.keep_alive_pdu.pack()

        self.pdu_conf.file_flag = LargeFileFlag.LARGE
        keep_alive_pdu_large = KeepAlivePdu(pdu_conf=self.pdu_conf, progress=0)
        keep_alive_pdu_invalid = keep_alive_pdu_large.pack()[:-1]
        with self.assertRaises(ValueError):
            KeepAlivePdu.unpack(bytes(keep_alive_pdu_invalid))

    def test_unpack(self):
        keep_alive_pdu_raw = self.keep_alive_pdu.pack()
        keep_alive_unpacked = KeepAlivePdu.unpack(data=keep_alive_pdu_raw)
        self.assertEqual(keep_alive_unpacked.packet_len, 12)
        self.assertEqual(keep_alive_unpacked.progress, 0)
        self.assertEqual(keep_alive_unpacked.direction, Direction.TOWARDS_SENDER)
        self.keep_alive_pdu.file_flag = LargeFileFlag.LARGE
        self.assertEqual(self.keep_alive_pdu.packet_len, 16)
        keep_alive_pdu_large = self.keep_alive_pdu.pack()
        self.assertEqual(len(keep_alive_pdu_large), 16)

    def test_print(self):
        print(self.keep_alive_pdu)
        self.assertEqual(
            self.keep_alive_pdu.__repr__(),
            (
                f"KeepAlivePdu(pdu_conf={self.keep_alive_pdu.pdu_file_directive.pdu_conf!r}, "
                f"progress=0)"
            ),
        )

    def test_from_factory(self):
        keep_alive_raw = self.keep_alive_pdu.pack()
        pdu_holder = PduFactory.from_raw_to_holder(keep_alive_raw)
        self.assertIsNotNone(pdu_holder.pdu)
        keep_alive_pdu = pdu_holder.to_keep_alive_pdu()
        self.assertIsNotNone(keep_alive_pdu)
        self.assertEqual(keep_alive_pdu, self.keep_alive_pdu)
