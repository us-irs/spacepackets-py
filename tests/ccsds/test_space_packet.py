from unittest import TestCase

from spacepackets import SequenceFlags, PacketType, SpacePacketHeader
from spacepackets.ccsds import PacketSeqCtrl, PacketId
from spacepackets.ccsds.spacepacket import (
    get_space_packet_id_bytes,
    get_sp_psc_raw,
    get_sp_packet_id_raw,
    SpacePacket,
    get_apid_from_raw_space_packet,
)


class TestSpacePacket(TestCase):
    def setUp(self) -> None:
        self.sp_header = SpacePacketHeader(
            apid=0x02,
            data_len=0x16,
            seq_count=0x34,
            sec_header_flag=True,
            packet_type=PacketType.TC,
            seq_flags=SequenceFlags.FIRST_SEGMENT,
        )

    def test_basic(self):
        self.assertEqual(self.sp_header.apid, 0x02)
        self.assertEqual(self.sp_header.seq_flags, SequenceFlags.FIRST_SEGMENT)
        self.assertEqual(self.sp_header.ccsds_version, 0b000)
        self.assertEqual(self.sp_header.seq_count, 0x34)
        self.assertEqual(self.sp_header.data_len, 0x16)
        self.assertEqual(self.sp_header.packet_type, PacketType.TC)

    def test_raw_output(self):
        raw_output = self.sp_header.pack()
        self.assertEqual(
            raw_output,
            bytes(
                [
                    0x18,  # TC, and secondary header flag is set -> 0b0001100 -> 0x18
                    0x02,  # APID 0x02
                    0x40,  # Sequence count is one byte value, so the only set bit here is the bit
                    # from the Sequence flag argument, which is the second bit for
                    # SequenceFlags.FIRST_SEGMENT
                    0x34,  # Sequence Count specified above
                    0x00,  # This byte and the next byte should be 22 big endian (packet length)
                    0x16,
                ]
            ),
        )

    def test_more_complex_output(self):
        # All ones, maximum value for APID
        self.sp_header.apid = pow(2, 11) - 1
        # All ones, maximum value for sequence count
        self.sp_header.seq_count = pow(2, 14) - 1
        self.sp_header.seq_flags = SequenceFlags.UNSEGMENTED
        self.sp_header.data_len = pow(2, 16) - 1
        raw_output = self.sp_header.pack()
        self.assertEqual(
            raw_output,
            bytes(
                [
                    0x1F,  # APID part is all ones, TC, sec header flag set -> 0b00011111
                    0xFF,
                    0xFF,  # All-Ones PSC
                    0xFF,
                    0xFF,  # This byte and the next byte should be 22 big endian (packet length)
                    0xFF,
                ]
            ),
        )

    def test_repr(self):
        self.assertEqual(
            f"{self.sp_header!r}",
            (
                f"SpacePacketHeader(packet_version=0, packet_type={PacketType.TC!r}, "
                f"apid={self.sp_header.apid}, seq_cnt={self.sp_header.seq_count}, "
                f"data_len={self.sp_header.data_len}, "
                f"sec_header_flag={self.sp_header.sec_header_flag}, "
                f"seq_flags={self.sp_header.seq_flags!r})"
            ),
        )

    def test_apid_from_raw(self):
        sp_packed = self.sp_header.pack()
        self.assertEqual(get_apid_from_raw_space_packet(raw_packet=sp_packed), 0x02)

    def test_apid_from_raw_invalid_input(self):
        with self.assertRaises(ValueError):
            get_apid_from_raw_space_packet(raw_packet=bytes())

    def test_unpack(self):
        sp_packed = self.sp_header.pack()
        sp_unpacked = SpacePacketHeader.unpack(data=sp_packed)
        self.assertEqual(sp_unpacked.packet_type, PacketType.TC)
        self.assertEqual(sp_unpacked.apid, 0x02)
        self.assertEqual(sp_unpacked.ccsds_version, 0b000)
        self.assertEqual(sp_unpacked.seq_count, 52)
        self.assertEqual(sp_unpacked.seq_flags, SequenceFlags.FIRST_SEGMENT)

    def test_invalid_apid(self):
        with self.assertRaises(ValueError):
            SpacePacketHeader(
                apid=982292, data_len=22, seq_count=52, packet_type=PacketType.TC
            )

    def test_invalid_data_len(self):
        self.assertRaises(
            ValueError,
            SpacePacketHeader,
            apid=0x02,
            data_len=679393,
            seq_count=52,
            packet_type=PacketType.TC,
        )

    def test_invalid_seq_count(self):
        self.assertRaises(
            ValueError,
            SpacePacketHeader,
            apid=0x02,
            data_len=22,
            seq_count=96030,
            packet_type=PacketType.TC,
        )

    def test_unpack_invalid_input(self):
        self.assertRaises(ValueError, SpacePacketHeader.unpack, bytearray())

    def test_print(self):
        print(self.sp_header)
        print(self.sp_header.__repr__())

    def test_sp_packet_id_bytes(self):
        byte_one, byte_two = get_space_packet_id_bytes(
            packet_type=PacketType.TC, apid=0x3FF, secondary_header_flag=True
        )
        self.assertEqual(byte_two, 0xFF)
        self.assertEqual(byte_one & 0x07, 0x03)

    def test_packet_id(self):
        byte_one, byte_two = get_space_packet_id_bytes(
            packet_type=PacketType.TC, apid=0x3FF, secondary_header_flag=True
        )
        packet_id_as_num = byte_one << 8 | byte_two
        packet_id = PacketId(ptype=PacketType.TC, apid=0x3FF, sec_header_flag=True)
        packet_id_raw = get_sp_packet_id_raw(
            packet_type=PacketType.TC, apid=0x3FF, secondary_header_flag=True
        )
        self.assertEqual(packet_id_as_num, packet_id.raw())
        self.assertEqual(packet_id_as_num, packet_id_raw)

    def test_packet_seq_ctrl(self):
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

    def test_from_composite_field(self):
        packet_id = PacketId(ptype=PacketType.TC, apid=0x3FF, sec_header_flag=True)
        psc = PacketSeqCtrl(seq_count=0x22, seq_flags=SequenceFlags.UNSEGMENTED)
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
            packet_type=PacketType.TM,
            seq_flags=SequenceFlags.UNSEGMENTED,
            apid=0x12,
            data_len=7,
            seq_count=28,
        )
        raw = header_tm.pack()
        header_tm_back = SpacePacketHeader.unpack(raw)
        self.assertEqual(header_tm_back.packet_type, PacketType.TM)
        self.assertEqual(header_tm_back.apid, 0x12)
        self.assertEqual(header_tm_back.ccsds_version, 0b000)
        self.assertEqual(header_tm_back.seq_count, 28)
        self.assertEqual(header_tm_back.data_len, 7)

    def test_to_space_packet(self):
        sph = SpacePacketHeader(
            PacketType.TC,
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
        sph.packet_type = PacketType.TM
        self.assertEqual(sph.packet_type, PacketType.TM)

    def test_sp_print(self):
        sph = SpacePacketHeader(
            PacketType.TC,
            apid=0x22,
            sec_header_flag=False,
            seq_flags=SequenceFlags.UNSEGMENTED,
            data_len=65,
            seq_count=22,
        )
        sp = SpacePacket(sp_header=sph, user_data=bytes([0, 1]), sec_header=None)
        print(sp)

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

        packet_id = PacketId(ptype=PacketType.TC, sec_header_flag=True, apid=0x7FF)
        self.assertEqual(
            f"{packet_id}",
            "Packet ID: [Packet Type: TC, Sec Header Flag: True, APID: 0x7ff]",
        )
        packet_id_raw = packet_id.raw()
        self.assertEqual(packet_id_raw, 0x1FFF)
        packet_id_from_raw = PacketId.from_raw(packet_id_raw)
        self.assertEqual(packet_id_from_raw.raw(), packet_id.raw())
        self.assertEqual(PacketId.empty().raw(), 0)

    def test_equality_sp_packet(self):
        sp = SpacePacket(
            sp_header=self.sp_header, sec_header=None, user_data=bytes([0, 1, 2])
        )
        other_sp = SpacePacket(
            sp_header=self.sp_header, sec_header=None, user_data=bytes([0, 1, 2])
        )
        self.assertEqual(sp, other_sp)
