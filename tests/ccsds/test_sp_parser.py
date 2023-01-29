from unittest import TestCase
from collections import deque

from spacepackets.ccsds import CdsShortTimestamp
from spacepackets.ccsds.spacepacket import parse_space_packets
from spacepackets.ecss.tm import PusTelemetry


class TestSpParser(TestCase):
    def test_sp_parser(self):
        tm_packet = PusTelemetry(
            service=17, subservice=2, time_provider=CdsShortTimestamp.empty()
        )
        packet_ids = (tm_packet.packet_id,)
        tm_packet_raw = tm_packet.pack()
        packet_deque = deque()
        packet_deque.appendleft(tm_packet_raw)
        packet_deque.appendleft(tm_packet_raw)
        sp_list = parse_space_packets(
            analysis_queue=packet_deque, packet_ids=packet_ids
        )
        self.assertEqual(len(sp_list), 2)
        self.assertEqual(sp_list[0], tm_packet_raw)
        self.assertEqual(sp_list[1], tm_packet_raw)

        other_larger_packet = PusTelemetry(
            service=8,
            subservice=128,
            source_data=bytearray(64),
            time_provider=CdsShortTimestamp.empty(),
        )
        other_larger_packet_raw = other_larger_packet.pack()
        packet_deque.appendleft(tm_packet_raw)
        packet_deque.appendleft(bytearray(8))
        packet_deque.appendleft(other_larger_packet_raw)
        sp_list = parse_space_packets(
            analysis_queue=packet_deque, packet_ids=packet_ids
        )
        self.assertEqual(len(sp_list), 2)
        self.assertEqual(sp_list[0], tm_packet_raw)
        self.assertEqual(sp_list[1], other_larger_packet_raw)

        packet_deque.appendleft(bytearray(3))
        sp_list = parse_space_packets(
            analysis_queue=packet_deque, packet_ids=packet_ids
        )
        self.assertEqual(len(sp_list), 0)
        sp_list = parse_space_packets(
            analysis_queue=packet_deque, packet_ids=packet_ids
        )
        self.assertEqual(len(sp_list), 0)

        # slice TM packet in half
        tm_packet_first_half = tm_packet_raw[:10]
        tm_packet_second_half = tm_packet_raw[10:]
        packet_deque.appendleft(tm_packet_first_half)
        sp_list = parse_space_packets(
            analysis_queue=packet_deque, packet_ids=packet_ids
        )
        self.assertEqual(len(sp_list), 0)
        self.assertEqual(len(packet_deque), 1)
        packet_deque.appendleft(tm_packet_second_half)
        sp_list = parse_space_packets(
            analysis_queue=packet_deque, packet_ids=packet_ids
        )
        self.assertEqual(len(sp_list), 1)
        self.assertEqual(len(packet_deque), 0)
        self.assertEqual(sp_list[0], tm_packet_raw)
