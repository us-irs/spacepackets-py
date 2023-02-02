from unittest import TestCase

from spacepackets.cfdp import LargeFileFlag, EntityIdTlv, NULL_CHECKSUM_U32
from spacepackets.cfdp.conf import PduConfig
from spacepackets.cfdp.pdu import EofPdu


class TestEofPdu(TestCase):
    def test_eof_pdu(self):
        pdu_conf = PduConfig.default()
        eof_pdu = EofPdu(
            file_checksum=NULL_CHECKSUM_U32, file_size=0, pdu_conf=pdu_conf
        )
        self.assertEqual(eof_pdu.pdu_file_directive.header_len, 8)
        expected_packet_len = 8 + 1 + 4 + 4
        self.assertEqual(eof_pdu.packet_len, expected_packet_len)
        eof_pdu_raw = eof_pdu.pack()
        expected_header = bytearray([0x20, 0x00, 0x0A, 0x11, 0x00, 0x00, 0x00, 0x04])
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
        eof_pdu.fault_location = fault_loc_tlv
        self.assertEqual(eof_pdu.packet_len, expected_packet_len + 4)
        eof_pdu_with_fault_loc = eof_pdu
        eof_pdu_with_fault_loc_raw = eof_pdu_with_fault_loc.pack()
        self.assertEqual(len(eof_pdu_with_fault_loc_raw), expected_packet_len + 4)
        eof_pdu_with_fault_loc_unpacked = EofPdu.unpack(data=eof_pdu_with_fault_loc_raw)
        self.assertEqual(
            eof_pdu_with_fault_loc_unpacked.fault_location.pack(), fault_loc_tlv.pack()
        )

        with self.assertRaises(ValueError):
            EofPdu(file_checksum=bytes([0x00]), file_size=0, pdu_conf=pdu_conf)

        pdu_conf.file_flag = LargeFileFlag.LARGE
        eof_pdu_large_file = EofPdu(
            file_checksum=NULL_CHECKSUM_U32, file_size=0, pdu_conf=pdu_conf
        )
        self.assertEqual(eof_pdu_large_file.packet_len, expected_packet_len + 4)
        eof_pdu_large_file_raw = eof_pdu_large_file.pack()
        self.assertEqual(len(eof_pdu_large_file_raw), expected_packet_len + 4)
