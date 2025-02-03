from collections import deque
from unittest import TestCase

from spacepackets.ccsds import CdsShortTimestamp
from spacepackets.ccsds.spacepacket import parse_space_packets, parse_space_packets_from_deque
from spacepackets.ecss.tm import PusTm


class TestSpParser(TestCase):
    def setUp(self) -> None:
        self.def_apid = 0x03
        self.tm_packet = PusTm(
            apid=self.def_apid,
            service=17,
            subservice=2,
            timestamp=CdsShortTimestamp.empty().pack(),
        )
        self.packet_ids = (self.tm_packet.packet_id,)
        self.tm_packet_raw = self.tm_packet.pack()
        self.packet_deque = deque()
        self.packet_buf = bytearray()

    def test_sp_parser(self):
        self.packet_buf.extend(self.tm_packet_raw)
        self.packet_buf.extend(self.tm_packet_raw)

        result = parse_space_packets(buf=self.packet_buf, packet_ids=self.packet_ids)
        self.assertEqual(len(result.tm_list), 2)
        self.assertEqual(result.tm_list[0], self.tm_packet_raw)
        self.assertEqual(result.tm_list[1], self.tm_packet_raw)
        self.assertEqual(result.scanned_bytes, len(self.tm_packet_raw) * 2)
        self.assertEqual(len(result.skipped_ranges), 0)

    def test_sp_parser_with_deque(self):
        self.packet_deque.append(self.tm_packet_raw)
        self.packet_deque.append(self.tm_packet_raw)
        result = parse_space_packets_from_deque(self.packet_deque, self.packet_ids)
        self.assertEqual(len(result.tm_list), 2)
        self.assertEqual(result.tm_list[0], self.tm_packet_raw)
        self.assertEqual(result.tm_list[1], self.tm_packet_raw)
        self.assertEqual(result.scanned_bytes, len(self.tm_packet_raw) * 2)
        self.assertEqual(len(result.skipped_ranges), 0)
        self.assertEqual(len(self.packet_deque), 2)
        flattened_deque = bytearray()
        while self.packet_deque:
            flattened_deque.extend(self.packet_deque.popleft())
        self.assertEqual(len(flattened_deque), len(self.tm_packet_raw) * 2)

    def test_sp_parser_crap_data_is_skipped(self):
        other_larger_packet = PusTm(
            apid=self.def_apid,
            service=8,
            subservice=128,
            source_data=bytearray(64),
            timestamp=CdsShortTimestamp.empty().pack(),
        )
        other_larger_packet_raw = other_larger_packet.pack()
        self.packet_buf.extend(self.tm_packet_raw)
        # Crap data, could also be a CCSDS packet with an unknown packet ID.
        self.packet_buf.extend(bytearray(8))
        self.packet_buf.extend(other_larger_packet_raw)
        result = parse_space_packets(self.packet_buf, packet_ids=self.packet_ids)
        self.assertEqual(len(result.tm_list), 2)
        self.assertEqual(result.tm_list[0], self.tm_packet_raw)
        self.assertEqual(result.tm_list[1], other_larger_packet_raw)
        self.assertEqual(
            result.skipped_ranges, [range(len(self.tm_packet_raw), len(self.tm_packet_raw) + 8)]
        )

    def test_sp_parser_crap_data(self):
        self.packet_buf.extend(bytearray(3))
        result = parse_space_packets(self.packet_buf, packet_ids=self.packet_ids)
        self.assertEqual(len(result.tm_list), 0)
        self.assertEqual(result.scanned_bytes, 0)
        self.assertEqual(result.skipped_ranges, [])

        self.packet_buf = bytearray(7)
        result = parse_space_packets(self.packet_buf, packet_ids=self.packet_ids)
        self.assertEqual(len(result.tm_list), 0)
        # Scanned one byte
        self.assertEqual(result.scanned_bytes, 1)
        self.assertEqual(result.skipped_ranges, [range(1)])

    def test_broken_packet(self):
        # slice TM packet in half
        tm_packet_first_half = self.tm_packet_raw[:10]
        tm_packet_second_half = self.tm_packet_raw[10:]
        self.packet_buf.extend(tm_packet_first_half)
        result = parse_space_packets(self.packet_buf, packet_ids=self.packet_ids)
        self.assertEqual(len(result.tm_list), 0)
        self.assertEqual(result.scanned_bytes, 0)
        self.packet_buf.extend(tm_packet_second_half)
        result = parse_space_packets(self.packet_buf, packet_ids=self.packet_ids)
        self.assertEqual(len(result.tm_list), 1)
        self.assertEqual(result.tm_list[0], self.tm_packet_raw)
        self.assertEqual(result.scanned_bytes, len(self.tm_packet_raw))

    def test_broken_packet_at_end(self):
        self.packet_buf.extend(self.tm_packet_raw)
        # slice TM packet in half
        tm_packet_first_half = self.tm_packet_raw[:10]
        self.packet_buf.extend(tm_packet_first_half)
        result = parse_space_packets(self.packet_buf, packet_ids=self.packet_ids)
        self.assertEqual(len(result.tm_list), 1)
        self.assertEqual(result.tm_list[0], self.tm_packet_raw)
        self.assertEqual(result.scanned_bytes, len(self.tm_packet_raw))
