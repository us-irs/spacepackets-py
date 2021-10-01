#!/usr/bin/env python3
import unittest

from unittest import TestCase
from crcmod import crcmod

from spacepackets.ecss.tc import PusTelecommand
from spacepackets.ecss.tc import generate_crc, generate_packet_crc
from spacepackets.ecss.conf import set_default_apid, get_default_apid


class TestTelecommand(TestCase):

    def test_generic(self):
        pus_17_telecommand = PusTelecommand(service=17, subservice=1, ssc=25)
        pus_17_telecommand.print()
        self.assertTrue(pus_17_telecommand.get_total_length() == len(pus_17_telecommand.pack()))
        command_tuple = pus_17_telecommand.pack_command_tuple()
        self.assertTrue(len(command_tuple[0]) == pus_17_telecommand.get_total_length())
        print(repr(pus_17_telecommand))
        print(pus_17_telecommand)
        self.assertTrue(pus_17_telecommand.get_packet_id() == (0x18 << 8 | 0xef))
        self.assertTrue(pus_17_telecommand.get_app_data() == bytearray())
        self.assertTrue(pus_17_telecommand.get_apid() == get_default_apid())

        set_default_apid(42)
        self.assertTrue(get_default_apid() == 42)

        test_app_data = bytearray([1, 2, 3])
        pus_17_telecommand_with_app_data = PusTelecommand(
            service=17, subservice=32, ssc=52, app_data=test_app_data
        )

        self.assertTrue(len(pus_17_telecommand_with_app_data.get_app_data()) == 3)
        self.assertTrue(pus_17_telecommand_with_app_data.get_app_data() == bytearray([1, 2, 3]))

        pus_17_telecommand_invalid = PusTelecommand(service=493, subservice=5252, ssc=99432942)
        self.assertTrue(pus_17_telecommand_invalid.get_service() == 0)
        self.assertTrue(pus_17_telecommand_invalid.get_subservice() == 0)
        self.assertTrue(pus_17_telecommand_invalid.get_ssc() == 0)

        invalid_input = "hello"
        self.assertTrue(pus_17_telecommand_invalid.get_data_length(
            app_data_len=invalid_input, secondary_header_len=0) == 0
        )
        self.assertRaises(TypeError, pus_17_telecommand_invalid.get_data_length(
            app_data_len=invalid_input, secondary_header_len=0)
        )

    def test_crc_16(self):
        pus_17_telecommand = PusTelecommand(service=17, subservice=1, ssc=25)
        crc_func = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0xFFFF, xorOut=0x0000)
        crc = crc_func(pus_17_telecommand.pack())
        self.assertTrue(crc == 0)

        test_data = bytearray([192, 23, 4, 82, 3, 6])
        data_with_crc = generate_crc(test_data)
        crc = crc_func(data_with_crc)
        self.assertTrue(crc == 0)

        packet_raw = pus_17_telecommand.pack()
        packet_raw[len(packet_raw) - 1] += 1
        self.assertTrue(crc_func(packet_raw) != 0)
        packet_raw = generate_packet_crc(packet_raw)
        self.assertTrue(crc_func(packet_raw) == 0)

    def test_getter_functions(self):
        pus_17_telecommand = PusTelecommand(service=17, subservice=1, ssc=25)
        self.assertTrue(pus_17_telecommand.get_ssc() == 25)
        self.assertTrue(pus_17_telecommand.get_service() == 17)
        self.assertTrue(pus_17_telecommand.get_subservice() == 1)


if __name__ == '__main__':
    unittest.main()
