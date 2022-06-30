from unittest import TestCase

import crcmod

from spacepackets.ecss import PusTelecommand, PusTcDataFieldHeader
from spacepackets.ecss.conf import get_default_tc_apid, set_default_tc_apid
from spacepackets.ecss.tc import generate_crc, generate_packet_crc
from spacepackets.util import PrintFormats


class TestTelecommand(TestCase):
    def test_generic(self):
        pus_17_telecommand = PusTelecommand(service=17, subservice=1, seq_count=25)
        pus_17_telecommand.print(PrintFormats.HEX)
        self.assertTrue(pus_17_telecommand.packet_len == len(pus_17_telecommand.pack()))
        command_tuple = pus_17_telecommand.pack_command_tuple()
        self.assertTrue(len(command_tuple[0]) == pus_17_telecommand.packet_len)
        print(repr(pus_17_telecommand))
        print(pus_17_telecommand)
        self.assertTrue(pus_17_telecommand.valid)
        self.assertTrue(pus_17_telecommand.packet_id.raw() == (0x18 << 8 | 0x00))
        self.assertTrue(pus_17_telecommand.app_data == bytearray())
        self.assertTrue(pus_17_telecommand.apid == get_default_tc_apid())

        set_default_tc_apid(42)
        self.assertTrue(get_default_tc_apid() == 42)

        test_app_data = bytearray([1, 2, 3])
        pus_17_telecommand_with_app_data = PusTelecommand(
            service=17, subservice=32, seq_count=52, app_data=test_app_data
        )

        self.assertTrue(len(pus_17_telecommand_with_app_data.app_data) == 3)
        self.assertTrue(
            pus_17_telecommand_with_app_data.app_data == bytearray([1, 2, 3])
        )
        with self.assertRaises(ValueError):
            PusTelecommand(service=493, subservice=5252, seq_count=99432942)

        pus_17_raw = pus_17_telecommand.pack()
        pus_17_unpacked = PusTelecommand.unpack(raw_packet=pus_17_raw)
        self.assertEqual(pus_17_unpacked.service, 17)
        self.assertEqual(pus_17_unpacked.subservice, 1)
        self.assertEqual(pus_17_unpacked.valid, True)
        self.assertEqual(pus_17_unpacked.seq_count, 25)

        with self.assertRaises(ValueError):
            PusTelecommand.unpack(raw_packet=pus_17_raw[:11])
        # Make CRC invalid
        pus_17_raw[-1] = pus_17_raw[-1] + 1
        pus_17_unpacked_invalid = PusTelecommand.unpack(raw_packet=pus_17_raw)
        self.assertFalse(pus_17_unpacked_invalid.valid)

        self.assertEqual(PusTcDataFieldHeader.get_header_size(), 5)

        tc_header_pus_c = PusTcDataFieldHeader(service=0, subservice=0)
        tc_header_pus_c_raw = tc_header_pus_c.pack()
        ccsds_packet = pus_17_telecommand.to_space_packet()
        self.assertEqual(ccsds_packet.apid, pus_17_telecommand.apid)
        self.assertEqual(ccsds_packet.pack(), pus_17_telecommand.pack())
        pus_17_from_composite_fields = PusTelecommand.from_composite_fields(
            sp_header=pus_17_telecommand.sp_header,
            sec_header=pus_17_telecommand.pus_tc_sec_header,
            app_data=pus_17_telecommand.app_data,
        )
        self.assertEqual(pus_17_from_composite_fields.pack(), pus_17_telecommand.pack())
        # Hand checked to see if all __repr__ were implemented properly
        print(f"{pus_17_telecommand!r}")

    def test_crc_16(self):
        pus_17_telecommand = PusTelecommand(service=17, subservice=1, seq_count=25)
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
        pus_17_telecommand = PusTelecommand(service=17, subservice=1, seq_count=25)
        self.assertTrue(pus_17_telecommand.seq_count == 25)
        self.assertTrue(pus_17_telecommand.service == 17)
        self.assertEqual(pus_17_telecommand.subservice, 1)
