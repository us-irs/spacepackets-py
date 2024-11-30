from unittest import TestCase

from spacepackets.cfdp import DirectiveType, PduFactory, TransmissionMode
from spacepackets.cfdp.conf import PduConfig
from spacepackets.cfdp.defs import CrcFlag, Direction, LargeFileFlag
from spacepackets.cfdp.pdu import NakPdu
from spacepackets.cfdp.pdu.nak import get_max_seg_reqs_for_max_packet_size_and_pdu_cfg
from spacepackets.util import ByteFieldU16


class TestNakPdu(TestCase):
    def setUp(self) -> None:
        self.pdu_conf = PduConfig(
            trans_mode=TransmissionMode.ACKNOWLEDGED,
            transaction_seq_num=ByteFieldU16(1),
            source_entity_id=ByteFieldU16(0),
            dest_entity_id=ByteFieldU16(1),
        )
        self.nak_pdu = NakPdu(start_of_scope=0, end_of_scope=200, pdu_conf=self.pdu_conf)

    def test_state(self):
        self.assertEqual(self.nak_pdu.segment_requests, [])
        pdu_header = self.nak_pdu.pdu_header
        self.assertEqual(pdu_header.direction, Direction.TOWARDS_SENDER)
        self.assertEqual(self.nak_pdu.directive_type, DirectiveType.NAK_PDU)
        # Start of scope (4) + end of scope (4) + directive code
        self.assertEqual(pdu_header.pdu_data_field_len, 8 + 1)
        self.assertEqual(pdu_header.file_flag, LargeFileFlag.NORMAL)
        self.assertEqual(pdu_header.transmission_mode, TransmissionMode.ACKNOWLEDGED)
        self.assertEqual(self.nak_pdu.file_flag, LargeFileFlag.NORMAL)
        self.assertEqual(self.nak_pdu.packet_len, 19)

    def test_segment_req_for_packet_size(self):
        pdu_conf = PduConfig.default()
        nak_pdu = NakPdu(pdu_conf, start_of_scope=0, end_of_scope=0)
        # 7 byte header, 1 byte directive, 8 bytes start and end of segment, leaves 48 bytes for
        # 6 segment requests (6 bytes each)
        self.assertEqual(
            6,
            get_max_seg_reqs_for_max_packet_size_and_pdu_cfg(
                max_packet_size=64, pdu_conf=PduConfig.default()
            ),
        )
        self.assertEqual(nak_pdu.get_max_seg_reqs_for_max_packet_size(64), 6)
        self.assertEqual(
            6,
            get_max_seg_reqs_for_max_packet_size_and_pdu_cfg(
                max_packet_size=65, pdu_conf=PduConfig.default()
            ),
        )
        self.assertEqual(nak_pdu.get_max_seg_reqs_for_max_packet_size(65), 6)
        self.assertEqual(
            5,
            get_max_seg_reqs_for_max_packet_size_and_pdu_cfg(
                max_packet_size=63, pdu_conf=PduConfig.default()
            ),
        )
        self.assertEqual(nak_pdu.get_max_seg_reqs_for_max_packet_size(63), 5)
        self.assertEqual(
            7,
            get_max_seg_reqs_for_max_packet_size_and_pdu_cfg(
                max_packet_size=72, pdu_conf=PduConfig.default()
            ),
        )
        self.assertEqual(nak_pdu.get_max_seg_reqs_for_max_packet_size(72), 7)

    def test_segment_req_for_packet_size_large_file(self):
        # 7 byte header, 1 byte directive, 16 bytes start and end of segment, leaves 48 bytes for
        # 3 large segment requests (16 bytes each)
        pdu_conf = PduConfig.default()
        pdu_conf.file_flag = LargeFileFlag.LARGE
        nak_pdu = NakPdu(pdu_conf, start_of_scope=0, end_of_scope=0)
        self.assertEqual(
            3,
            get_max_seg_reqs_for_max_packet_size_and_pdu_cfg(max_packet_size=72, pdu_conf=pdu_conf),
        )
        self.assertEqual(nak_pdu.get_max_seg_reqs_for_max_packet_size(72), 3)
        self.assertEqual(
            3,
            get_max_seg_reqs_for_max_packet_size_and_pdu_cfg(max_packet_size=73, pdu_conf=pdu_conf),
        )
        self.assertEqual(nak_pdu.get_max_seg_reqs_for_max_packet_size(73), 3)
        self.assertEqual(
            2,
            get_max_seg_reqs_for_max_packet_size_and_pdu_cfg(max_packet_size=71, pdu_conf=pdu_conf),
        )
        self.assertEqual(nak_pdu.get_max_seg_reqs_for_max_packet_size(71), 2)
        self.assertEqual(
            4,
            get_max_seg_reqs_for_max_packet_size_and_pdu_cfg(max_packet_size=88, pdu_conf=pdu_conf),
        )
        self.assertEqual(nak_pdu.get_max_seg_reqs_for_max_packet_size(88), 4)

    def test_segment_req_for_packet_size_large_file_with_crc(self):
        # 7 byte header, 1 byte directive, 16 bytes start and end of segment, leaves 48 bytes for
        # 3 large segment requests (16 bytes each)
        pdu_conf = PduConfig.default()
        pdu_conf.file_flag = LargeFileFlag.LARGE
        pdu_conf.crc_flag = CrcFlag.WITH_CRC
        nak_pdu = NakPdu(pdu_conf, start_of_scope=0, end_of_scope=0)
        self.assertEqual(
            3,
            get_max_seg_reqs_for_max_packet_size_and_pdu_cfg(max_packet_size=74, pdu_conf=pdu_conf),
        )
        self.assertEqual(nak_pdu.get_max_seg_reqs_for_max_packet_size(74), 3)
        self.assertEqual(
            2,
            get_max_seg_reqs_for_max_packet_size_and_pdu_cfg(max_packet_size=73, pdu_conf=pdu_conf),
        )
        self.assertEqual(nak_pdu.get_max_seg_reqs_for_max_packet_size(73), 2)
        self.assertEqual(
            4,
            get_max_seg_reqs_for_max_packet_size_and_pdu_cfg(max_packet_size=90, pdu_conf=pdu_conf),
        )
        self.assertEqual(nak_pdu.get_max_seg_reqs_for_max_packet_size(90), 4)

    def test_segment_req_for_packet_error(self):
        pdu_conf = PduConfig.default()
        nak_pdu = NakPdu(pdu_conf, start_of_scope=0, end_of_scope=0)
        self.assertEqual(
            0,
            get_max_seg_reqs_for_max_packet_size_and_pdu_cfg(
                max_packet_size=16, pdu_conf=PduConfig.default()
            ),
        )
        self.assertEqual(nak_pdu.get_max_seg_reqs_for_max_packet_size(16), 0)
        with self.assertRaises(ValueError):
            self.assertEqual(
                0,
                get_max_seg_reqs_for_max_packet_size_and_pdu_cfg(
                    max_packet_size=15, pdu_conf=PduConfig.default()
                ),
            )
        with self.assertRaises(ValueError):
            self.assertEqual(nak_pdu.get_max_seg_reqs_for_max_packet_size(15), 0)

    def test_packing_0(self):
        nak_packed = self.nak_pdu.pack()
        self.assertEqual(len(nak_packed), 19)
        self.nak_pdu.file_flag = LargeFileFlag.LARGE
        pdu_header = self.nak_pdu.pdu_header
        self.assertEqual(pdu_header.file_flag, LargeFileFlag.LARGE)
        self.assertEqual(self.nak_pdu.file_flag, LargeFileFlag.LARGE)
        self.assertEqual(self.nak_pdu.packet_len, 27)
        nak_packed = self.nak_pdu.pack()
        self.assertEqual(len(nak_packed), 27)

    def test_packing_1(self):
        self.nak_pdu.file_flag = LargeFileFlag.NORMAL
        pdu_header = self.nak_pdu.pdu_header
        self.assertEqual(pdu_header.file_flag, LargeFileFlag.NORMAL)
        self.assertEqual(self.nak_pdu.file_flag, LargeFileFlag.NORMAL)
        self.assertEqual(self.nak_pdu.packet_len, 19)
        nak_packed = self.nak_pdu.pack()
        self.assertEqual(len(nak_packed), 19)

    def test_invalid_scopes(self):
        self.nak_pdu.start_of_scope = pow(2, 32) + 1
        self.nak_pdu.end_of_scope = pow(2, 32) + 1
        self.assertRaises(ValueError, self.nak_pdu.pack)

    def test_with_file_segments_0(self):
        self.nak_pdu.start_of_scope = 0
        self.nak_pdu.end_of_scope = 200
        segment_requests = [(20, 40), (60, 80)]
        self.nak_pdu.segment_requests = segment_requests
        self.assertEqual(self.nak_pdu.segment_requests, segment_requests)
        # Additional 2 segment requests, each has size 8
        self.assertEqual(self.nak_pdu.packet_len, 35)
        nak_packed = self.nak_pdu.pack()
        self.assertEqual(len(nak_packed), 35)
        nak_unpacked = NakPdu.unpack(data=nak_packed)
        self.assertEqual(nak_unpacked.pack(), nak_packed)

    def test_with_file_segments_1(self):
        self.nak_pdu.start_of_scope = 0
        self.nak_pdu.end_of_scope = 200
        segment_requests = [(20, 40), (60, 80)]
        self.nak_pdu.file_flag = LargeFileFlag.LARGE
        self.nak_pdu.segment_requests = segment_requests
        self.assertEqual(self.nak_pdu.segment_requests, segment_requests)
        # 2 segment requests with size 16 each plus 16 for start and end of scope
        self.assertEqual(self.nak_pdu.pdu_file_directive.pdu_header.header_len, 10)
        self.assertEqual(self.nak_pdu.pdu_file_directive.header_len, 11)
        self.assertEqual(self.nak_pdu.packet_len, 11 + 48)
        nak_packed = self.nak_pdu.pack()
        self.assertEqual(len(nak_packed), 59)
        nak_unpacked = NakPdu.unpack(data=nak_packed)
        self.assertEqual(nak_unpacked.pack(), nak_packed)

    def test_roundtrip_with_file_segments_and_crc(self):
        self.nak_pdu.start_of_scope = 0
        self.nak_pdu.end_of_scope = 200
        segment_requests = [(20, 40), (60, 80)]
        self.nak_pdu.pdu_header.crc_flag = CrcFlag.WITH_CRC
        self.nak_pdu.segment_requests = segment_requests
        nak_raw = self.nak_pdu.pack()
        nak_unpacked = NakPdu.unpack(nak_raw)
        self.assertEqual(nak_unpacked, self.nak_pdu)
        self.assertEqual(nak_unpacked.pack(), self.nak_pdu.pack())

    def test_nak_pdu_errors(self):
        self.nak_pdu.start_of_scope = 0
        self.nak_pdu.end_of_scope = 200
        segment_requests = [(20, 40), (60, 80)]
        self.nak_pdu.file_flag = LargeFileFlag.LARGE
        self.nak_pdu.segment_requests = segment_requests
        nak_packed = self.nak_pdu.pack()
        nak_packed.append(0)
        self.assertRaises(ValueError, NakPdu.unpack, data=nak_packed)
        self.nak_pdu.segment_requests = []
        self.assertEqual(self.nak_pdu.packet_len, 59 - 32)
        nak_packed = self.nak_pdu.pack()
        self.assertEqual(len(nak_packed), 59 - 32)

        self.nak_pdu.file_flag = LargeFileFlag.NORMAL
        segment_requests = [(pow(2, 32) + 1, 40), (60, 80)]
        self.nak_pdu.segment_requests = segment_requests
        self.assertRaises(ValueError, self.nak_pdu.pack)

    def test_from_factory(self):
        nak_pdu_raw = self.nak_pdu.pack()
        pdu_holder = PduFactory.from_raw_to_holder(nak_pdu_raw)
        self.assertIsNotNone(pdu_holder.pdu)
        nak_pdu = pdu_holder.to_nak_pdu()
        self.assertIsNotNone(nak_pdu)
        self.assertEqual(nak_pdu, self.nak_pdu)
