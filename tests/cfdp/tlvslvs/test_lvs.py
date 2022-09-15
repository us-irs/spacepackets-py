from unittest import TestCase

from spacepackets.cfdp.lv import CfdpLv
from spacepackets.cfdp.tlv import CfdpTlv


class TestLvs(TestCase):
    def test_lvs(self):
        test_values = bytes([0, 1, 2])
        test_lv = CfdpLv(value=test_values)
        self.assertEqual(test_lv.value, test_values)
        self.assertEqual(test_lv.len, 3)
        self.assertEqual(test_lv.packet_len, 4)
        test_lv_packed = test_lv.pack()
        self.assertEqual(len(test_lv_packed), 4)
        self.assertEqual(test_lv_packed[0], 3)
        self.assertEqual(test_lv_packed[1 : 1 + 3], test_values)

        CfdpLv.unpack(raw_bytes=test_lv_packed)
        self.assertEqual(test_lv.value, test_values)
        self.assertEqual(test_lv.len, 3)
        self.assertEqual(test_lv.packet_len, 4)

        # Too much too pack
        faulty_values = bytearray(300)
        self.assertRaises(ValueError, CfdpLv, faulty_values)
        # Too large to unpack
        faulty_values[0] = 20
        self.assertRaises(ValueError, CfdpLv.unpack, faulty_values[0:15])
        # Too short to unpack
        faulty_lv = bytes([0])
        self.assertRaises(ValueError, CfdpTlv.unpack, faulty_lv)

    def test_equal(self):
        test_lv = CfdpLv(value=bytes([0, 1, 2, 3, 4]))
        lv_raw = test_lv.pack()
        lv_unpacked = CfdpLv.unpack(lv_raw)
        self.assertEqual(test_lv, lv_unpacked)

    def test_lv_print(self):
        test_lv = CfdpLv(value=bytes([0, 1, 2, 3, 4]))
        print(test_lv)
        print(f"{test_lv!r}")
