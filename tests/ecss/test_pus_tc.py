from unittest import TestCase

import crcmod

from spacepackets import SpacePacketHeader, PacketType
from spacepackets.ecss import PusTelecommand, PusTcDataFieldHeader, check_pus_crc
from spacepackets.ecss.conf import get_default_tc_apid, set_default_tc_apid, PusVersion
from spacepackets.ecss.tc import generate_crc, generate_packet_crc, InvalidTcCrc16


class TestTelecommand(TestCase):
    def setUp(self) -> None:
        self.ping_tc = PusTelecommand(
            service=17, subservice=1, seq_count=0x34, apid=0x02
        )
        self.ping_tc_raw = self.ping_tc.pack()

    def test_state(self):
        self.assertTrue(self.ping_tc.packet_len == len(self.ping_tc.pack()))
        command_raw = self.ping_tc.pack()
        self.assertTrue(len(command_raw) == self.ping_tc.packet_len)

        # 6 bytes CCSDS header, 5 bytes secondary header, 2 bytes CRC
        self.assertEqual(self.ping_tc.packet_len, 13)
        self.assertTrue(isinstance(self.ping_tc.crc16, bytes))
        self.assertTrue(len(self.ping_tc.crc16), 2)
        # The data length field is the full packet length minus the primary header minus 1
        self.assertEqual(self.ping_tc.sp_header.data_len, 6)
        self.assertEqual(self.ping_tc.packet_id.raw(), (0x18 << 8 | 0x02))
        self.assertEqual(self.ping_tc.app_data, bytearray())
        self.assertEqual(self.ping_tc.apid, 0x02)

    def test_valid_crc(self):
        self.assertTrue(check_pus_crc(self.ping_tc_raw))

    def test_packed(self):
        self.assertEqual(self.ping_tc_raw[0], 0x18)
        self.assertEqual(self.ping_tc_raw[1], 0x02)
        # D
        self.assertEqual(self.ping_tc_raw[2], 0xC0)
        # Sequence count is only in lower byte, is small enough
        self.assertEqual(self.ping_tc_raw[3], 0x34)
        # Data length 6, packed big endian
        self.assertEqual(self.ping_tc_raw[4], 0x00)
        self.assertEqual(self.ping_tc_raw[5], 0x06)
        # PUS Version C
        self.assertEqual(self.ping_tc_raw[6] >> 4 & 0b1111, PusVersion.PUS_C)
        # All ack fields is default
        self.assertEqual(self.ping_tc_raw[6] & 0b1111, 0b1111)
        # Service and subservice
        self.assertEqual(self.ping_tc_raw[7], 17)
        self.assertEqual(self.ping_tc_raw[8], 1)
        # Source ID
        self.assertEqual(self.ping_tc_raw[9] << 8 | self.ping_tc_raw[10], 0)
        # CRC is checked separately, still check raw value
        self.assertEqual(self.ping_tc_raw[11], 0xEE)
        self.assertEqual(self.ping_tc_raw[12], 0x63)
        self.assertEqual(self.ping_tc.crc16, self.ping_tc_raw[11:13])

    def test_source_id(self):
        self.assertEqual(self.ping_tc.source_id, 0)
        self.ping_tc.source_id = 12
        self.assertEqual(self.ping_tc.source_id, 12)

    def test_from_sph(self):
        sp = SpacePacketHeader(
            apid=0x02, packet_type=PacketType.TC, seq_count=0x34, data_len=0
        )
        ping_tc_from_sph = PusTelecommand.from_sp_header(
            sp_header=sp, service=17, subservice=1
        )
        self.assertEqual(self.ping_tc, ping_tc_from_sph)

    def test_custom_source_id(self):
        source_id = 0x5FF
        self.ping_tc.source_id = source_id
        raw = self.ping_tc.pack()
        self.assertEqual(raw[9] << 8 | raw[10], 0x5FF)

    def test_unpack_too_short(self):
        too_short = bytearray([1, 2, 3])
        with self.assertRaises(ValueError):
            PusTelecommand.unpack(too_short)

    def test_equality(self):
        ping_raw_unpacked = PusTelecommand.unpack(self.ping_tc_raw)
        self.assertEqual(ping_raw_unpacked, self.ping_tc)

    def test_print(self):
        print(repr(self.ping_tc))
        print(self.ping_tc)

        set_default_tc_apid(42)
        self.assertTrue(get_default_tc_apid() == 42)

    def test_with_app_data(self):
        test_app_data = bytearray([1, 2, 3])
        ping_with_app_data = PusTelecommand(
            service=17, subservice=32, seq_count=52, app_data=test_app_data
        )
        # 6 bytes CCSDS header, 5 bytes secondary header, 2 bytes CRC, 3 bytes app data
        self.assertEqual(ping_with_app_data.packet_len, 16)
        # The data length field is the full packet length minus the primary header minus 1
        self.assertEqual(ping_with_app_data.sp_header.data_len, 9)

        self.assertTrue(len(ping_with_app_data.app_data) == 3)
        self.assertTrue(ping_with_app_data.app_data == bytearray([1, 2, 3]))
        raw_with_app_data = ping_with_app_data.pack()
        self.assertEqual(raw_with_app_data[11], 1)
        self.assertEqual(raw_with_app_data[12], 2)
        self.assertEqual(raw_with_app_data[13], 3)

    def test_invalid_seq_count(self):
        with self.assertRaises(ValueError):
            PusTelecommand(service=493, subservice=5252, seq_count=99432942)

    def test_unpack(self):
        pus_17_unpacked = PusTelecommand.unpack(data=self.ping_tc_raw)
        self.assertEqual(pus_17_unpacked.service, 17)
        self.assertEqual(pus_17_unpacked.subservice, 1)
        self.assertEqual(pus_17_unpacked.seq_count, 0x34)
        self.assertEqual(self.ping_tc.crc16, pus_17_unpacked.crc16)

    def test_faulty_unpack(self):
        with self.assertRaises(ValueError):
            PusTelecommand.unpack(data=self.ping_tc_raw[:11])

    def test_invalid_crc(self):
        # Make CRC invalid
        self.ping_tc_raw[-1] = self.ping_tc_raw[-1] + 1
        with self.assertRaises(InvalidTcCrc16):
            PusTelecommand.unpack(data=self.ping_tc_raw)
        self.assertEqual(PusTcDataFieldHeader.get_header_size(), 5)

    def test_to_space_packet(self):
        ccsds_packet = self.ping_tc.to_space_packet()
        self.assertEqual(ccsds_packet.apid, self.ping_tc.apid)
        self.assertEqual(ccsds_packet.pack(), self.ping_tc.pack())

    def test_sec_header(self):
        tc_header_pus_c = PusTcDataFieldHeader(service=1, subservice=2)
        tc_header_pus_c_raw = tc_header_pus_c.pack()
        # TODO: Some more tests?
        self.assertEqual(tc_header_pus_c_raw[1], 1)
        self.assertEqual(tc_header_pus_c_raw[2], 2)

    def test_calc_crc(self):
        new_ping_tc = PusTelecommand(service=17, subservice=1)
        self.assertIsNone(new_ping_tc.crc16)
        new_ping_tc.calc_crc()
        self.assertIsNotNone(new_ping_tc.crc16)
        self.assertTrue(isinstance(new_ping_tc.crc16, bytes))
        self.assertEqual(len(new_ping_tc.crc16), 2)

    def test_crc_always_calced_if_none(self):
        new_ping_tc = PusTelecommand(service=17, subservice=1)
        self.assertIsNone(new_ping_tc.crc16)
        # Should still calculate CRC
        tc_raw = new_ping_tc.pack(recalc_crc=False)
        # Will throw invalid CRC16 error if CRC was not calculated
        tc_unpacked = PusTelecommand.unpack(tc_raw)
        self.assertEqual(tc_unpacked, new_ping_tc)

    def test_from_composite_fields(self):
        pus_17_from_composite_fields = PusTelecommand.from_composite_fields(
            sp_header=self.ping_tc.sp_header,
            sec_header=self.ping_tc.pus_tc_sec_header,
            app_data=self.ping_tc.app_data,
        )
        self.assertEqual(pus_17_from_composite_fields.pack(), self.ping_tc.pack())

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
