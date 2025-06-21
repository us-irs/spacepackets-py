from unittest import TestCase

from spacepackets.cfdp import NULL_CHECKSUM_U32, CrcFlag, LargeFileFlag
from spacepackets.cfdp.conf import PduConfig
from spacepackets.cfdp.defs import Direction
from spacepackets.cfdp.pdu import EofPdu, PduFactory
from spacepackets.cfdp.tlv import EntityIdTlv


class TestEofPdu(TestCase):
    def setUp(self) -> None:
        self.pdu_conf = PduConfig.default()
        self.eof_pdu = EofPdu(file_checksum=NULL_CHECKSUM_U32, file_size=0, pdu_conf=self.pdu_conf)

    def test_eof_pdu(self):
        self.assertEqual(self.eof_pdu.pdu_file_directive.header_len, 8)
        self.assertEqual(self.eof_pdu.direction, Direction.TOWARDS_RECEIVER)
        expected_packet_len = 8 + 1 + 4 + 4
        self.assertEqual(self.eof_pdu.packet_len, expected_packet_len)
        eof_pdu_raw = self.eof_pdu.pack()
        expected_header = bytearray([0x20, 0x00, 0x0A, 0x00, 0x00, 0x00, 0x00, 0x04])
        expected_header.append(0)
        expected_header.extend(NULL_CHECKSUM_U32)
        # File size is 0 as 4 bytes
        expected_header.extend(bytes([0x00, 0x00, 0x00, 0x00]))
        self.assertEqual(eof_pdu_raw, expected_header)
        eof_unpacked = EofPdu.unpack(data=eof_pdu_raw)
        self.assertEqual(eof_unpacked.pack(), eof_pdu_raw)
        eof_pdu_raw = eof_pdu_raw[:-2]
        with self.assertRaises(ValueError):
            EofPdu.unpack(data=eof_pdu_raw)

        fault_loc_tlv = EntityIdTlv(entity_id=bytes([0x00, 0x01]))
        self.assertEqual(fault_loc_tlv.packet_len, 4)
        self.eof_pdu.fault_location = fault_loc_tlv
        self.assertEqual(self.eof_pdu.packet_len, expected_packet_len + 4)
        eof_pdu_with_fault_loc = self.eof_pdu
        eof_pdu_with_fault_loc_raw = eof_pdu_with_fault_loc.pack()
        self.assertEqual(len(eof_pdu_with_fault_loc_raw), expected_packet_len + 4)
        eof_pdu_with_fault_loc_unpacked = EofPdu.unpack(data=eof_pdu_with_fault_loc_raw)
        self.assertEqual(
            eof_pdu_with_fault_loc_unpacked.fault_location.pack(), fault_loc_tlv.pack()
        )

        with self.assertRaises(ValueError):
            EofPdu(file_checksum=bytes([0x00]), file_size=0, pdu_conf=self.pdu_conf)

    def test_large_file_flag(self):
        expected_packet_len = 8 + 1 + 4 + 8
        self.pdu_conf.file_flag = LargeFileFlag.LARGE
        eof_pdu_large_file = EofPdu(
            file_checksum=NULL_CHECKSUM_U32, file_size=0, pdu_conf=self.pdu_conf
        )
        self.assertEqual(eof_pdu_large_file.direction, Direction.TOWARDS_RECEIVER)
        self.assertEqual(eof_pdu_large_file.packet_len, expected_packet_len)
        eof_pdu_large_file_raw = eof_pdu_large_file.pack()
        self.assertEqual(len(eof_pdu_large_file_raw), expected_packet_len)

    def test_with_crc(self):
        self.pdu_conf.crc_flag = CrcFlag.WITH_CRC
        eof = EofPdu(file_checksum=0, file_size=0, pdu_conf=self.pdu_conf)
        expected_packet_len = eof.header_len + 1 + 4 + 4 + 2
        self.assertEqual(eof.packet_len, expected_packet_len)
        eof_raw = eof.pack()
        self.assertEqual(len(eof_raw), expected_packet_len)
        # verify we can round-trip pack/unpack
        eof_unpacked = EofPdu.unpack(data=eof_raw)
        self.assertEqual(eof_unpacked, eof)
        self.assertEqual(eof_unpacked.pack(), eof.pack())

    def test_from_factory(self):
        eof_pdu_raw = self.eof_pdu.pack()
        pdu_holder = PduFactory.from_raw_to_holder(eof_pdu_raw)
        self.assertIsNotNone(pdu_holder.pdu)
        eof_pdu = pdu_holder.to_eof_pdu()
        self.assertIsNotNone(eof_pdu)
        self.assertEqual(eof_pdu, self.eof_pdu)
