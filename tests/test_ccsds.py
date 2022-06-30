from unittest import TestCase
from collections import deque

from spacepackets.ccsds.spacepacket import (
    get_sp_psc_raw,
    SpacePacketHeader,
    PacketTypes,
    get_space_packet_id_bytes,
    get_sp_packet_id_raw,
    SequenceFlags,
    get_apid_from_raw_space_packet,
    parse_space_packets,
    PacketId,
    PacketSeqCtrl,
    SpacePacket,
)
from spacepackets.ecss.tm import PusTelemetry, PusVersion


class TestCcsds(TestCase):
    def test_utility(self):
        psc = PacketSeqCtrl(
            seq_flags=SequenceFlags.UNSEGMENTED, seq_count=pow(2, 14) - 1
        )
        self.assertEqual(
            f"{psc}",
            f"PSC: [Seq Flags: UNSEG, Seq Count: {pow(2, 14) - 1}]",
        )
        psc_raw = psc.raw()
        self.assertEqual(psc_raw, 0xFFFF)
        psc_from_raw = PacketSeqCtrl.from_raw(psc_raw)
        self.assertEqual(psc_from_raw.raw(), psc.raw())
        self.assertEqual(PacketSeqCtrl.empty().raw(), 0)

        packet_id = PacketId(ptype=PacketTypes.TC, sec_header_flag=True, apid=0x7FF)
        self.assertEqual(
            f"{packet_id}",
            f"Packet ID: [Packet Type: TC, Sec Header Flag: True, APID: 0x7ff]",
        )
        packet_id_raw = packet_id.raw()
        self.assertEqual(packet_id_raw, 0x1FFF)
        packet_id_from_raw = PacketId.from_raw(packet_id_raw)
        self.assertEqual(packet_id_from_raw.raw(), packet_id.raw())
        self.assertEqual(PacketId.empty().raw(), 0)

    def test_spacepacket(self):
        sp_header = SpacePacketHeader(
            apid=0x02,
            data_len=22,
            seq_count=52,
            packet_type=PacketTypes.TC,
            seq_flags=SequenceFlags.FIRST_SEGMENT,
        )
        self.assertEqual(sp_header.apid, 0x02)
        self.assertEqual(sp_header.seq_count, 52)
        self.assertEqual(sp_header.data_len, 22)
        self.assertEqual(sp_header.packet_type, PacketTypes.TC)
        sp_packed = sp_header.pack()
        self.assertEqual(get_apid_from_raw_space_packet(raw_packet=sp_packed), 0x02)
        self.assertRaises(
            ValueError, get_apid_from_raw_space_packet, raw_packet=bytearray()
        )
        sp_unpacked = SpacePacketHeader.unpack(space_packet_raw=sp_packed)
        self.assertRaises(
            ValueError,
            SpacePacketHeader,
            apid=982292,
            data_len=22,
            seq_count=52,
            packet_type=PacketTypes.TC,
        )
        self.assertRaises(
            ValueError,
            SpacePacketHeader,
            apid=0x02,
            data_len=679393,
            seq_count=52,
            packet_type=PacketTypes.TC,
        )
        self.assertRaises(
            ValueError,
            SpacePacketHeader,
            apid=0x02,
            data_len=22,
            seq_count=96030,
            packet_type=PacketTypes.TC,
        )
        self.assertRaises(ValueError, SpacePacketHeader.unpack, bytearray())
        self.assertEqual(sp_unpacked.packet_type, PacketTypes.TC)
        self.assertEqual(sp_unpacked.apid, 0x02)
        self.assertEqual(sp_unpacked.ccsds_version, 0b000)
        self.assertEqual(sp_unpacked.seq_count, 52)
        self.assertEqual(sp_unpacked.seq_flags, SequenceFlags.FIRST_SEGMENT)
        print(sp_header)
        print(sp_header.__repr__())

        byte_one, byte_two = get_space_packet_id_bytes(
            packet_type=PacketTypes.TC, apid=0x3FF, secondary_header_flag=True
        )
        self.assertEqual(byte_two, 0xFF)
        self.assertEqual(byte_one & 0x07, 0x03)
        packet_id_as_num = byte_one << 8 | byte_two
        packet_id = PacketId(ptype=PacketTypes.TC, apid=0x3FF, sec_header_flag=True)
        packet_id_raw = get_sp_packet_id_raw(
            packet_type=PacketTypes.TC, apid=0x3FF, secondary_header_flag=True
        )
        self.assertEqual(packet_id_as_num, packet_id.raw())

        psc = PacketSeqCtrl(seq_count=0x22, seq_flags=SequenceFlags.UNSEGMENTED)
        psc_raw = get_sp_psc_raw(seq_count=0x22, seq_flags=SequenceFlags.UNSEGMENTED)
        self.assertEqual(psc_raw, psc.raw())
        sequence_flags_raw = psc.seq_flags
        ssc_raw = psc.seq_count
        self.assertEqual(sequence_flags_raw, SequenceFlags.UNSEGMENTED)
        self.assertEqual(ssc_raw, 0x22)
        self.assertRaises(
            ValueError,
            get_sp_psc_raw,
            seq_count=0xFFFF,
            seq_flags=SequenceFlags.UNSEGMENTED,
        )

        raw_header = SpacePacketHeader.from_composite_fields(
            packet_id=packet_id, psc=psc, data_length=22
        ).pack()
        self.assertEqual(raw_header[0], ((packet_id.raw() & 0xFF00) >> 8) & 0x1FFF)
        self.assertEqual(raw_header[1], packet_id.raw() & 0xFF)
        self.assertEqual(raw_header[2], (psc.raw() & 0xFF00) >> 8)
        self.assertEqual(raw_header[3], psc.raw() & 0xFF)
        self.assertEqual(raw_header[4], (22 & 0xFF00) >> 8)
        self.assertEqual(raw_header[5], 22 & 0xFF)

        header_from_composite = SpacePacketHeader.from_composite_fields(
            packet_id=packet_id, psc=psc, data_length=22
        )
        self.assertEqual(header_from_composite.pack(), raw_header)
        header_tm = SpacePacketHeader(
            packet_type=PacketTypes.TM,
            seq_flags=SequenceFlags.UNSEGMENTED,
            apid=0x12,
            data_len=7,
            seq_count=28,
        )
        raw = header_tm.pack()
        header_tm_back = SpacePacketHeader.unpack(raw)
        self.assertEqual(header_tm_back.packet_type, PacketTypes.TM)
        self.assertEqual(header_tm_back.apid, 0x12)
        self.assertEqual(header_tm_back.ccsds_version, 0b000)
        self.assertEqual(header_tm_back.seq_count, 28)
        self.assertEqual(header_tm_back.data_len, 7)

        sph = SpacePacketHeader(
            PacketTypes.TC,
            apid=0x22,
            sec_header_flag=False,
            seq_flags=SequenceFlags.UNSEGMENTED,
            data_len=65,
            seq_count=22,
        )
        self.assertEqual(sph.header_len, 6)
        # User data mandatory
        with self.assertRaises(ValueError):
            SpacePacket(sp_header=sph, sec_header=None, user_data=None).pack()
        sph.sec_header_flag = True
        # Secondary header mandatory
        with self.assertRaises(ValueError):
            SpacePacket(sp_header=sph, sec_header=None, user_data=None).pack()
        sph.packet_type = PacketTypes.TM
        self.assertEqual(sph.packet_type, PacketTypes.TM)
        sp = SpacePacket(sp_header=sph, user_data=bytes([0, 1]), sec_header=None)
        print(sp)

    def test_sp_parser(self):
        tm_packet = PusTelemetry(service=17, subservice=2)
        packet_ids = (tm_packet.packet_id.raw(),)
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
