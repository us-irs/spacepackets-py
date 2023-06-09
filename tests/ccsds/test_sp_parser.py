from unittest import TestCase
from collections import deque

from spacepackets.ccsds import CdsShortTimestamp
from spacepackets.ccsds.spacepacket import parse_space_packets
from spacepackets.ecss.tm import PusTelemetry


class TestSpParser(TestCase):
    def setUp(self) -> None:
        self.tm_packet = PusTelemetry(
            service=17, subservice=2, time_provider=CdsShortTimestamp.empty()
        )
        self.packet_ids = (self.tm_packet.packet_id,)
        self.tm_packet_raw = self.tm_packet.pack()
        self.packet_deque = deque()

    def test_sp_parser(self):
        self.packet_deque.appendleft(self.tm_packet_raw)
        self.packet_deque.appendleft(self.tm_packet_raw)
        sp_list = parse_space_packets(
            analysis_queue=self.packet_deque, packet_ids=self.packet_ids
        )
        self.assertEqual(len(sp_list), 2)
        self.assertEqual(sp_list[0], self.tm_packet_raw)
        self.assertEqual(sp_list[1], self.tm_packet_raw)

    def test_sp_parser_crap_data_is_skipped(self):
        other_larger_packet = PusTelemetry(
            service=8,
            subservice=128,
            source_data=bytearray(64),
            time_provider=CdsShortTimestamp.empty(),
        )
        other_larger_packet_raw = other_larger_packet.pack()
        self.packet_deque.appendleft(self.tm_packet_raw)
        self.packet_deque.appendleft(bytearray(8))
        self.packet_deque.appendleft(other_larger_packet_raw)
        sp_list = parse_space_packets(
            analysis_queue=self.packet_deque, packet_ids=self.packet_ids
        )
        self.assertEqual(len(sp_list), 2)
        self.assertEqual(sp_list[0], self.tm_packet_raw)
        self.assertEqual(sp_list[1], other_larger_packet_raw)

    def test_sp_parser_crap_data(self):
        self.packet_deque.appendleft(bytearray(3))
        sp_list = parse_space_packets(
            analysis_queue=self.packet_deque, packet_ids=self.packet_ids
        )
        self.assertEqual(len(sp_list), 0)
        sp_list = parse_space_packets(
            analysis_queue=self.packet_deque, packet_ids=self.packet_ids
        )
        self.assertEqual(len(sp_list), 0)

    def test_broken_packet(self):
        # slice TM packet in half
        tm_packet_first_half = self.tm_packet_raw[:10]
        tm_packet_second_half = self.tm_packet_raw[10:]
        self.packet_deque.appendleft(tm_packet_first_half)
        sp_list = parse_space_packets(
            analysis_queue=self.packet_deque, packet_ids=self.packet_ids
        )
        self.assertEqual(len(sp_list), 0)
        self.assertEqual(len(self.packet_deque), 1)
        self.packet_deque.appendleft(tm_packet_second_half)
        sp_list = parse_space_packets(
            analysis_queue=self.packet_deque, packet_ids=self.packet_ids
        )
        self.assertEqual(len(sp_list), 1)
        self.assertEqual(len(self.packet_deque), 0)
        self.assertEqual(sp_list[0], self.tm_packet_raw)

    def test_broken_packet_at_end(self):
        self.packet_deque.appendleft(self.tm_packet_raw)
        # slice TM packet in half
        tm_packet_first_half = self.tm_packet_raw[:10]
        self.packet_deque.appendleft(tm_packet_first_half)
        sp_list = parse_space_packets(
            analysis_queue=self.packet_deque, packet_ids=self.packet_ids
        )
        self.assertEqual(len(sp_list), 1)
        self.assertEqual(len(self.packet_deque), 1)
        self.assertEqual(self.packet_deque.pop(), tm_packet_first_half)
        self.assertEqual(sp_list[0], self.tm_packet_raw)
