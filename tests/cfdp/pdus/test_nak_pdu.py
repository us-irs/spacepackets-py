from unittest import TestCase

from spacepackets.cfdp import TransmissionMode
from spacepackets.cfdp.conf import PduConfig
from spacepackets.cfdp.defs import Direction, LargeFileFlag
from spacepackets.cfdp.pdu import NakPdu
from spacepackets.util import ByteFieldU16


class TestNakPdu(TestCase):
    def test_nak_pdu(self):
        pdu_conf = PduConfig(
            trans_mode=TransmissionMode.ACKNOWLEDGED,
            transaction_seq_num=ByteFieldU16(1),
            source_entity_id=ByteFieldU16(0),
            dest_entity_id=ByteFieldU16(1),
        )
        nak_pdu = NakPdu(start_of_scope=0, end_of_scope=200, pdu_conf=pdu_conf)
        self.assertEqual(nak_pdu.segment_requests, [])
        pdu_header = nak_pdu.pdu_file_directive.pdu_header
        self.assertEqual(pdu_header.direction, Direction.TOWARDS_RECEIVER)
        # Start of scope (4) + end of scope (4) + directive code
        self.assertEqual(pdu_header.pdu_data_field_len, 8 + 1)
        self.assertEqual(pdu_header.file_flag, LargeFileFlag.NORMAL)
        self.assertEqual(pdu_header.trans_mode, TransmissionMode.ACKNOWLEDGED)
        self.assertEqual(nak_pdu.file_flag, LargeFileFlag.NORMAL)
        self.assertEqual(nak_pdu.packet_len, 19)
        nak_packed = nak_pdu.pack()
        self.assertEqual(len(nak_packed), 19)
        nak_pdu.file_flag = LargeFileFlag.LARGE
        self.assertEqual(pdu_header.file_flag, LargeFileFlag.LARGE)
        self.assertEqual(nak_pdu.file_flag, LargeFileFlag.LARGE)
        self.assertEqual(nak_pdu.packet_len, 27)
        nak_packed = nak_pdu.pack()
        self.assertEqual(len(nak_packed), 27)

        nak_pdu.file_flag = LargeFileFlag.NORMAL
        self.assertEqual(pdu_header.file_flag, LargeFileFlag.NORMAL)
        self.assertEqual(nak_pdu.file_flag, LargeFileFlag.NORMAL)
        self.assertEqual(nak_pdu.packet_len, 19)
        nak_packed = nak_pdu.pack()
        self.assertEqual(len(nak_packed), 19)

        nak_pdu.start_of_scope = pow(2, 32) + 1
        nak_pdu.end_of_scope = pow(2, 32) + 1
        self.assertRaises(ValueError, nak_pdu.pack)

        nak_pdu.start_of_scope = 0
        nak_pdu.end_of_scope = 200
        segment_requests = [(20, 40), (60, 80)]
        nak_pdu.segment_requests = segment_requests
        self.assertEqual(nak_pdu.segment_requests, segment_requests)
        # Additional 2 segment requests, each has size 8
        self.assertEqual(nak_pdu.packet_len, 35)
        nak_packed = nak_pdu.pack()
        self.assertEqual(len(nak_packed), 35)
        nak_unpacked = NakPdu.unpack(data=nak_packed)
        self.assertEqual(nak_unpacked.pack(), nak_packed)

        nak_pdu.file_flag = LargeFileFlag.LARGE
        # 2 segment requests with size 16 each plus 16 for start and end of scope
        self.assertEqual(nak_pdu.pdu_file_directive.pdu_header.header_len, 10)
        self.assertEqual(nak_pdu.pdu_file_directive.header_len, 11)
        self.assertEqual(nak_pdu.packet_len, 11 + 48)
        nak_packed = nak_pdu.pack()
        self.assertEqual(len(nak_packed), 59)
        nak_repacked = nak_unpacked.pack()
        nak_unpacked = NakPdu.unpack(data=nak_packed)
        self.assertEqual(nak_unpacked.pack(), nak_packed)
        nak_repacked.append(0)
        self.assertRaises(ValueError, NakPdu.unpack, data=nak_repacked)
        nak_pdu.segment_requests = []
        self.assertEqual(nak_pdu.packet_len, 59 - 32)
        nak_packed = nak_pdu.pack()
        self.assertEqual(len(nak_packed), 59 - 32)

        nak_pdu.file_flag = LargeFileFlag.NORMAL
        segment_requests = [(pow(2, 32) + 1, 40), (60, 80)]
        nak_pdu.segment_requests = segment_requests
        self.assertRaises(ValueError, nak_pdu.pack)
