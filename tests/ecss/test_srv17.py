from unittest import TestCase

from spacepackets.ccsds import CdsShortTimestamp
from spacepackets.ccsds.spacepacket import PacketType, SequenceFlags
from spacepackets.ecss import PusService
from spacepackets.ecss.pus_17_test import Service17Tm

from .common import TEST_STAMP, generic_time_provider_mock


class TestSrv17Tm(TestCase):
    def setUp(self) -> None:
        self.def_apid = 0x05
        self.srv17_tm = Service17Tm(apid=self.def_apid, subservice=1, timestamp=b"")
        self.srv17_tm.pus_tm.apid = 0x72
        self.time_stamp_provider = generic_time_provider_mock(TEST_STAMP)

    def test_state(self):
        self.assertEqual(self.srv17_tm.sp_header, self.srv17_tm.pus_tm.space_packet_header)
        self.assertEqual(self.srv17_tm.service, PusService.S17_TEST)
        self.assertEqual(self.srv17_tm.subservice, 1)
        self.assertEqual(self.srv17_tm.timestamp, b"")
        self.assertEqual(self.srv17_tm.apid, 0x72)
        self.assertEqual(self.srv17_tm.seq_count, 0)
        self.assertEqual(self.srv17_tm.seq_flags, SequenceFlags.UNSEGMENTED)
        self.assertEqual(self.srv17_tm.packet_type, PacketType.TM)
        self.assertTrue(self.srv17_tm.sec_header_flag)
        self.assertEqual(self.srv17_tm.source_data, b"")

    def test_other_state(self):
        srv17_with_data = Service17Tm(
            apid=self.def_apid,
            subservice=128,
            timestamp=CdsShortTimestamp(0, 0).pack(),
            source_data=bytes([0, 1, 2]),
        )
        self.assertEqual(srv17_with_data.source_data, bytes([0, 1, 2]))

        self.assertEqual(
            CdsShortTimestamp.unpack(srv17_with_data.timestamp), CdsShortTimestamp(0, 0)
        )

    def test_service_17_tm(self):
        srv_17_tm = Service17Tm(apid=self.def_apid, subservice=2, timestamp=TEST_STAMP)
        self.assertEqual(srv_17_tm.pus_tm.subservice, 2)
        srv_17_tm_raw = srv_17_tm.pack()
        srv_17_tm_unpacked = Service17Tm.unpack(data=srv_17_tm_raw, timestamp_len=len(TEST_STAMP))
        self.assertEqual(srv_17_tm_unpacked.pus_tm.subservice, 2)
