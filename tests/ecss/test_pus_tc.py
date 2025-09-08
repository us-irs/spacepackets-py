from __future__ import annotations

import struct
from unittest import TestCase

import fastcrc

from spacepackets import PacketType, SpacePacketHeader
from spacepackets.ccsds.spacepacket import CCSDS_HEADER_LEN, SequenceFlags
from spacepackets.ecss import (
    PusTc,
    PusTcDataFieldHeader,
    PusVersion,
    check_pus_crc,
    peek_pus_packet_info,
)
from spacepackets.ecss.tc import InvalidTcCrc16Error, generate_crc, generate_packet_crc


class TestTelecommand(TestCase):
    def setUp(self) -> None:
        self.ping_tc = PusTc(service=17, subservice=1, seq_count=0x34, apid=0x02)
        self.ping_tc_no_checksum = PusTc(
            service=17, subservice=1, seq_count=0x34, apid=0x02, has_checksum=False
        )

    def generic_test_state(self, tc: PusTc, with_checksum: bool):
        packet_len = 13
        if not with_checksum:
            packet_len -= 2
        # 6 bytes CCSDS header, 5 bytes secondary header, 2 bytes CRC
        self.assertEqual(tc.packet_len, packet_len)
        # The data length field is the full packet length minus the primary header minus 1
        self.assertEqual(tc.sp_header.data_len, packet_len - CCSDS_HEADER_LEN - 1)
        self.assertEqual(tc.packet_id.raw(), (0x18 << 8 | 0x02))
        self.assertEqual(tc.app_data, bytearray())
        self.assertEqual(tc.apid, 0x02)
        self.assertEqual(tc.packet_type, PacketType.TC)
        self.assertEqual(tc.seq_flags, SequenceFlags.UNSEGMENTED)
        self.assertEqual(tc.seq_count, 0x34)
        self.assertTrue(tc.sec_header_flag, True)
        command_raw = tc.pack()
        self.assertTrue(len(command_raw) == tc.packet_len)

    def test_state_with_checksum(self):
        self.generic_test_state(self.ping_tc, with_checksum=True)
        self.assertTrue(isinstance(self.ping_tc.crc16, bytes))
        assert self.ping_tc.crc16 is not None
        self.assertTrue(len(self.ping_tc.crc16), 2)

    def test_state_without_checksum(self):
        self.generic_test_state(self.ping_tc_no_checksum, with_checksum=False)
        self.assertIsNone(self.ping_tc_no_checksum.crc16)

    def test_peek(self):
        packet_info = peek_pus_packet_info(self.ping_tc.pack())
        self.assertEqual(packet_info.sp_header, self.ping_tc.sp_header)
        self.assertEqual(packet_info.pus_version, PusVersion.PUS_C)

    def test_valid_crc(self):
        self.assertTrue(check_pus_crc(self.ping_tc.pack()))

    def generic_test_packed(self, tc_raw: bytes | bytearray):
        self.assertEqual(tc_raw[0], 0x18)
        self.assertEqual(tc_raw[1], 0x02)
        # D
        self.assertEqual(tc_raw[2], 0xC0)
        # Sequence count is only in lower byte, is small enough
        self.assertEqual(tc_raw[3], 0x34)
        # Data length 6, packed big endian
        data_len = struct.unpack("!H", tc_raw[4:6])[0]
        self.assertEqual(data_len, len(tc_raw) - CCSDS_HEADER_LEN - 1)
        # PUS Version C
        self.assertEqual(tc_raw[6] >> 4 & 0b1111, PusVersion.PUS_C)
        # All ack fields is default
        self.assertEqual(tc_raw[6] & 0b1111, 0b1111)
        # Service and subservice
        self.assertEqual(tc_raw[7], 17)
        self.assertEqual(tc_raw[8], 1)
        # Source ID
        self.assertEqual(tc_raw[9] << 8 | tc_raw[10], 0)

    def test_pack_with_checksum(self):
        tc_raw = self.ping_tc.pack()
        self.generic_test_packed(tc_raw)
        self.assertEqual(self.ping_tc.crc16, tc_raw[11:13])
        # CRC is checked separately, still check raw value
        self.assertEqual(tc_raw[11], 0xEE)
        self.assertEqual(tc_raw[12], 0x63)

    def test_pack_without_checksum(self):
        tc_raw = self.ping_tc_no_checksum.pack()
        self.generic_test_packed(tc_raw)

    def test_source_id(self):
        self.assertEqual(self.ping_tc.source_id, 0)
        self.ping_tc.source_id = 12
        self.assertEqual(self.ping_tc.source_id, 12)

    def test_from_sph(self):
        sp = SpacePacketHeader(apid=0x02, packet_type=PacketType.TC, seq_count=0x34, data_len=0)
        ping_tc_from_sph = PusTc.from_sp_header(sp_header=sp, service=17, subservice=1)
        self.assertEqual(self.ping_tc, ping_tc_from_sph)

    def test_custom_source_id(self):
        source_id = 0x5FF
        self.ping_tc.source_id = source_id
        raw = self.ping_tc.pack()
        self.assertEqual(raw[9] << 8 | raw[10], 0x5FF)

    def test_unpack_too_short(self):
        too_short = bytearray([1, 2, 3])
        with self.assertRaises(ValueError):
            PusTc.unpack(too_short)

    def test_equality(self):
        ping_raw_unpacked = PusTc.unpack(self.ping_tc.pack())
        self.assertEqual(ping_raw_unpacked, self.ping_tc)

    def test_print(self):
        print(repr(self.ping_tc))
        print(self.ping_tc)

    def test_with_app_data(self):
        test_app_data = bytearray([1, 2, 3])
        ping_with_app_data = PusTc(
            apid=0, service=17, subservice=32, seq_count=52, app_data=test_app_data
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
            PusTc(apid=55, service=493, subservice=5252, seq_count=99432942)

    def common_unpack_checks(self, tc: PusTc):
        self.assertEqual(tc.service, 17)
        self.assertEqual(tc.subservice, 1)
        self.assertEqual(tc.seq_count, 0x34)
        self.assertEqual(tc.app_data, bytearray())
        self.assertEqual(tc.apid, 0x2)

    def test_unpack_with_checksum(self):
        pus_17_unpacked = PusTc.unpack(data=self.ping_tc.pack())
        self.common_unpack_checks(pus_17_unpacked)
        self.assertEqual(self.ping_tc.crc16, pus_17_unpacked.crc16)

    def test_unpack_without_checksum(self):
        pus_17_unpacked = PusTc.unpack_no_checksum(data=self.ping_tc_no_checksum.pack())
        self.common_unpack_checks(pus_17_unpacked)
        self.assertEqual(pus_17_unpacked.app_data, bytearray())

    def test_unpack_no_crc_check(self):
        pus_17_unpacked = PusTc.unpack_generic(
            data=self.ping_tc.pack(), has_checksum=True, verify_checksum=False
        )
        # CRC16 is still cached.
        self.assertEqual(pus_17_unpacked, self.ping_tc)
        pus_17_unpacked_2 = PusTc.unpack_no_checksum(data=self.ping_tc_no_checksum.pack())
        self.assertEqual(pus_17_unpacked_2.app_data, pus_17_unpacked.app_data)

    def test_faulty_unpack(self):
        with self.assertRaises(ValueError):
            PusTc.unpack(data=self.ping_tc.pack()[:11])

    def test_invalid_crc(self):
        # Make CRC invalid
        ping_tc_raw = self.ping_tc.pack()
        ping_tc_raw[-1] = ping_tc_raw[-1] + 1
        with self.assertRaises(InvalidTcCrc16Error):
            PusTc.unpack(data=ping_tc_raw)
        self.assertEqual(PusTcDataFieldHeader.get_header_size(), 5)

    def test_invalid_crc_ignored(self):
        # Make CRC invalid
        ping_tc_raw = self.ping_tc.pack()
        ping_tc_raw[-1] = ping_tc_raw[-1] + 1
        # Does not care
        pus_17_unpacked = PusTc.unpack_generic(
            data=ping_tc_raw, has_checksum=True, verify_checksum=False
        )
        self.assertEqual(pus_17_unpacked.sp_header, self.ping_tc.sp_header)
        self.assertEqual(pus_17_unpacked.pus_tc_sec_header, self.ping_tc.pus_tc_sec_header)

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
        new_ping_tc = PusTc(apid=27, service=17, subservice=1)
        self.assertIsNone(new_ping_tc.crc16)
        new_ping_tc.calc_crc()
        assert new_ping_tc.crc16 is not None
        self.assertTrue(isinstance(new_ping_tc.crc16, bytes))
        self.assertEqual(len(new_ping_tc.crc16), 2)

    def test_crc_always_calced_if_none(self):
        new_ping_tc = PusTc(apid=28, service=17, subservice=1)
        self.assertIsNone(new_ping_tc.crc16)
        # Should still calculate CRC
        tc_raw = new_ping_tc.pack(recalc_crc=False)
        # Will throw invalid CRC16 error if CRC was not calculated
        tc_unpacked = PusTc.unpack(tc_raw)
        self.assertEqual(tc_unpacked, new_ping_tc)

    def test_from_composite_fields(self):
        pus_17_from_composite_fields = PusTc.from_composite_fields(
            sp_header=self.ping_tc.sp_header,
            sec_header=self.ping_tc.pus_tc_sec_header,
            app_data=self.ping_tc.app_data,
        )
        self.assertEqual(pus_17_from_composite_fields.pack(), self.ping_tc.pack())

    def test_crc_16(self):
        pus_17_telecommand = PusTc(apid=25, service=17, subservice=1, seq_count=25)
        crc = fastcrc.crc16.ibm_3740(bytes(pus_17_telecommand.pack()))
        self.assertTrue(crc == 0)

        test_data = bytearray([192, 23, 4, 82, 3, 6])
        data_with_crc = generate_crc(test_data)
        crc = fastcrc.crc16.ibm_3740(bytes(data_with_crc))
        self.assertTrue(crc == 0)

        packet_raw = pus_17_telecommand.pack()
        packet_raw[len(packet_raw) - 1] += 1
        self.assertTrue(fastcrc.crc16.ibm_3740(bytes(packet_raw)) != 0)
        packet_raw = generate_packet_crc(packet_raw)
        self.assertTrue(fastcrc.crc16.ibm_3740(packet_raw) == 0)

    def test_getter_functions(self):
        pus_17_telecommand = PusTc(apid=26, service=17, subservice=1, seq_count=25)
        self.assertTrue(pus_17_telecommand.seq_count == 25)
        self.assertTrue(pus_17_telecommand.service == 17)
        self.assertEqual(pus_17_telecommand.subservice, 1)
