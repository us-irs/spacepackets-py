#!/usr/bin/env python3
import struct
from unittest import TestCase
from unittest.mock import MagicMock, PropertyMock

from crcmod.predefined import mkPredefinedCrcFun

from spacepackets.ccsds.spacepacket import (
    PacketId,
    PacketType,
    PacketSeqCtrl,
    SequenceFlags,
    SpacePacketHeader,
)
from spacepackets.ecss import PacketFieldEnum, check_pus_crc
from spacepackets.ecss.conf import set_default_tm_apid
from spacepackets.util import PrintFormats
from spacepackets.ecss.tm import (
    PusTelemetry,
    CdsShortTimestamp,
    PusVersion,
    PusTmSecondaryHeader,
)
from spacepackets.ecss.pus_17_test import Service17Tm
from spacepackets.ecss.pus_1_verification import (
    RequestId,
    VerificationParams,
    FailureNotice,
    StepId,
    ErrorCode,
)


class TestTelemetry(TestCase):
    def setUp(self) -> None:
        self.time_stamp_provider = MagicMock(spec=CdsShortTimestamp)
        len_mock = PropertyMock(return_value=7)
        type(self.time_stamp_provider).len_packed = len_mock
        self.raw_stamp = bytes([0, 1, 2, 3, 4, 5, 6])
        self.time_stamp_provider.pack.return_value = self.raw_stamp
        self.ping_reply = PusTelemetry(
            service=17,
            subservice=2,
            apid=0x123,
            seq_count=0x234,
            source_data=bytearray(),
            time_provider=self.time_stamp_provider,
        )
        self.ping_reply_raw = self.ping_reply.pack()

    def test_state(self):
        self.assertEqual(self.ping_reply.sp_header, self.ping_reply.space_packet_header)
        self.assertEqual(
            self.ping_reply.get_source_data_string(PrintFormats.HEX), "hex []"
        )
        self.assertEqual(
            self.ping_reply.get_source_data_string(PrintFormats.DEC), "dec []"
        )
        self.assertEqual(
            self.ping_reply.get_source_data_string(PrintFormats.BIN), "bin []"
        )
        self.assertEqual(self.ping_reply.subservice, 2)
        self.assertEqual(self.ping_reply.service, 17)
        self.assertEqual(self.ping_reply.apid, 0x123)
        self.assertEqual(self.ping_reply.seq_count, 0x234)
        self.assertEqual(self.ping_reply.space_packet_header.data_len, 15)
        self.assertEqual(self.ping_reply.packet_len, 22)

    def test_valid_crc(self):
        self.assertTrue(check_pus_crc(self.ping_reply_raw))

    def test_no_timestamp(self):
        self.ping_reply = PusTelemetry(
            service=17,
            subservice=2,
            apid=0x123,
            seq_count=0x234,
            source_data=bytearray(),
            time_provider=None,
        )
        self.assertEqual(self.ping_reply.pus_tm_sec_header.time_provider, None)
        tm_raw = self.ping_reply.pack()
        self.assertEqual(self.ping_reply.packet_len, 15)
        self.assertEqual(len(tm_raw), 15)
        self.raw_check_before_stamp()

    def raw_check_before_stamp(self):
        # Secondary header is set -> 0b0000_1001 , APID occupies last bit of first byte
        self.assertEqual(self.ping_reply_raw[0], 0x09)
        # Rest of APID
        self.assertEqual(self.ping_reply_raw[1], 0x23)
        # Unsegmented is the default, and first byte of 0x234 occupies this byte as well
        self.assertEqual(self.ping_reply_raw[2], 0xC2)
        self.assertEqual(self.ping_reply_raw[3], 0x34)
        self.assertEqual((self.ping_reply_raw[4] << 8) | self.ping_reply_raw[5], 15)
        # SC time ref status is 0
        self.assertEqual(self.ping_reply_raw[6], PusVersion.PUS_C << 4)
        self.assertEqual(self.ping_reply_raw[7], 17)
        self.assertEqual(self.ping_reply_raw[8], 2)
        # MSG counter
        self.assertEqual(self.ping_reply_raw[9], 0x00)
        self.assertEqual(self.ping_reply_raw[10], 0x00)
        # Destination ID
        self.assertEqual(self.ping_reply_raw[11], 0x00)
        self.assertEqual(self.ping_reply_raw[12], 0x00)

    def test_raw(self):
        self.raw_check_before_stamp()
        self.assertEqual(self.ping_reply_raw[13 : 13 + 7], self.raw_stamp)
        # CRC16-CCITT checksum
        crc_func = mkPredefinedCrcFun(crc_name="crc-ccitt-false")
        data_to_check = self.ping_reply_raw[0:20]
        crc16 = crc_func(data_to_check)
        self.assertEqual(crc16, struct.unpack("!H", self.ping_reply_raw[20:22])[0])

    def test_state_setting(self):
        self.ping_reply.space_packet_header.apid = 0x22
        source_data = bytearray([0x42, 0x38])
        self.ping_reply.tm_data = source_data
        self.assertEqual(self.ping_reply.apid, 0x22)
        self.assertEqual(
            self.ping_reply.pus_tm_sec_header.pus_version, PusVersion.PUS_C
        )
        self.assertTrue(self.ping_reply.valid)
        self.assertEqual(self.ping_reply.tm_data, source_data)
        self.assertEqual(self.ping_reply.packet_id.raw(), 0x0822)
        self.assertEqual(self.ping_reply.packet_len, 24)

    def test_service_from_raw(self):
        self.assertEqual(
            PusTelemetry.service_from_bytes(raw_bytearray=self.ping_reply_raw), 17
        )

    def test_service_from_raw_invalid(self):
        self.assertRaises(ValueError, PusTelemetry.service_from_bytes, bytearray())

    def test_source_data_string_getters(self):
        set_default_tm_apid(0x22)
        source_data = bytearray([0x42, 0x38])
        self.ping_reply.tm_data = source_data
        self.assertEqual(
            self.ping_reply.get_source_data_string(PrintFormats.HEX), "hex [42,38]"
        )
        self.assertEqual(
            self.ping_reply.get_source_data_string(PrintFormats.DEC), "dec [66,56]"
        )
        self.assertEqual(
            self.ping_reply.get_source_data_string(PrintFormats.BIN),
            "bin [\n0:01000010\n1:00111000\n]",
        )

    def test_print(self):
        self.ping_reply.print_full_packet_string(PrintFormats.HEX)

    def test_sec_header(self):
        raw_secondary_packet_header = self.ping_reply.pus_tm_sec_header.pack()
        self.assertEqual(raw_secondary_packet_header[0], 0x20)
        # Service
        self.assertEqual(raw_secondary_packet_header[1], 17)
        # Subservice
        self.assertEqual(raw_secondary_packet_header[2], 2)

    def test_full_printout(self):
        crc16 = self.ping_reply.crc16
        crc_string = f"{(crc16 & 0xff00) >> 8:02x},{crc16 & 0xff:02x}"
        raw_space_packet_header = self.ping_reply.space_packet_header.pack()
        sp_header_as_str = raw_space_packet_header.hex(sep=",", bytes_per_sep=1)
        raw_secondary_packet_header = self.ping_reply.pus_tm_sec_header.pack()
        second_header_as_str = raw_secondary_packet_header.hex(sep=",", bytes_per_sep=1)
        expected_printout = f"hex [{sp_header_as_str},{second_header_as_str},"
        expected_printout += f"{crc_string}]"
        self.assertEqual(
            self.ping_reply.get_full_packet_string(PrintFormats.HEX), expected_printout
        )

    def test_print_2(self):
        print(self.ping_reply)
        print(self.ping_reply.__repr__())

    def test_unpack(self):
        source_data = bytearray([0x42, 0x38])
        self.ping_reply.tm_data = source_data
        self.ping_reply.space_packet_header.apid = 0x22
        self.ping_reply_raw = self.ping_reply.pack()
        self.time_stamp_provider.read_from_raw = MagicMock()
        pus_17_tm_unpacked = PusTelemetry.unpack(
            raw_telemetry=self.ping_reply_raw, time_reader=self.time_stamp_provider
        )
        self.assertEqual(pus_17_tm_unpacked, self.ping_reply)

        self.assertEqual(pus_17_tm_unpacked.apid, 0x22)
        self.assertEqual(
            pus_17_tm_unpacked.pus_tm_sec_header.pus_version, PusVersion.PUS_C
        )
        self.assertTrue(pus_17_tm_unpacked.valid)
        pus_17_tm_unpacked.pus_tm_sec_header.time_provider.read_from_raw.assert_called_once()
        pus_17_tm_unpacked.pus_tm_sec_header.time_provider.read_from_raw.assert_called_with(
            self.raw_stamp
        )
        self.assertEqual(pus_17_tm_unpacked.tm_data, source_data)
        self.assertEqual(pus_17_tm_unpacked.packet_id.raw(), 0x0822)

        correct_size = self.ping_reply_raw[4] << 8 | self.ping_reply_raw[5]
        # Set length field invalid
        self.ping_reply_raw[4] = 0x00
        self.ping_reply_raw[5] = 0x00
        self.assertRaises(
            ValueError,
            PusTelemetry.unpack,
            self.ping_reply_raw,
            CdsShortTimestamp.empty(),
        )
        self.ping_reply_raw[4] = 0xFF
        self.ping_reply_raw[5] = 0xFF
        self.assertRaises(
            ValueError,
            PusTelemetry.unpack,
            self.ping_reply_raw,
            CdsShortTimestamp.empty(),
        )

        self.ping_reply_raw[4] = (correct_size & 0xFF00) >> 8
        self.ping_reply_raw[5] = correct_size & 0xFF
        self.ping_reply_raw.append(0)
        # Should work with a warning
        pus_17_tm_unpacked = PusTelemetry.unpack(
            raw_telemetry=self.ping_reply_raw, time_reader=self.time_stamp_provider
        )

        # This should cause the CRC calculation to fail
        incorrect_size = correct_size + 1
        self.ping_reply_raw[4] = (incorrect_size & 0xFF00) >> 8
        self.ping_reply_raw[5] = incorrect_size & 0xFF
        pus_17_tm_unpacked = PusTelemetry.unpack(
            raw_telemetry=self.ping_reply_raw, time_reader=self.time_stamp_provider
        )

    def test_faulty_unpack(self):
        self.assertRaises(ValueError, PusTelemetry.unpack, None, None)
        self.assertRaises(ValueError, PusTelemetry.unpack, bytearray(), None)

    def test_invalid_sec_header_unpack(self):
        invalid_secondary_header = bytearray([0x20, 0x00, 0x01, 0x06])
        self.assertRaises(
            ValueError, PusTmSecondaryHeader.unpack, invalid_secondary_header, None
        )

    def test_sp_header_getter(self):
        sp_header = self.ping_reply.sp_header
        self.assertEqual(sp_header.apid, 0x123)
        self.assertEqual(sp_header.packet_type, PacketType.TM)
        self.assertEqual(sp_header, self.ping_reply.space_packet_header)

    def test_space_packet_conversion(self):
        ccsds_packet = self.ping_reply.to_space_packet()
        self.assertEqual(ccsds_packet.apid, self.ping_reply.apid)
        self.assertEqual(ccsds_packet.pack(), self.ping_reply.pack())
        self.assertEqual(ccsds_packet.seq_count, self.ping_reply.seq_count)
        self.assertEqual(ccsds_packet.sec_header_flag, True)
        pus_17_from_composite_fields = PusTelemetry.from_composite_fields(
            sp_header=self.ping_reply.space_packet_header,
            sec_header=self.ping_reply.pus_tm_sec_header,
            tm_data=self.ping_reply.tm_data,
        )
        self.assertEqual(pus_17_from_composite_fields.pack(), self.ping_reply.pack())

    def test_faulty_sec_header(self):
        with self.assertRaises(ValueError):
            # Message Counter too large
            PusTmSecondaryHeader(
                service=0,
                subservice=0,
                time_provider=CdsShortTimestamp.from_now(),
                message_counter=129302,
            )

    def test_invalid_raw_size(self):
        # Set length field invalid
        self.ping_reply_raw[4] = 0x00
        self.ping_reply_raw[5] = 0x00
        self.assertRaises(ValueError, PusTelemetry.unpack, self.ping_reply_raw, None)

    def test_service_17_tm(self):
        srv_17_tm = Service17Tm(subservice=2, time_provider=self.time_stamp_provider)
        self.assertEqual(srv_17_tm.pus_tm.subservice, 2)
        srv_17_tm_raw = srv_17_tm.pack()
        srv_17_tm_unpacked = Service17Tm.unpack(
            raw_telemetry=srv_17_tm_raw, time_reader=self.time_stamp_provider
        )
        self.assertEqual(srv_17_tm_unpacked.pus_tm.subservice, 2)

    def test_req_id(self):
        tc_packet_id = PacketId(ptype=PacketType.TC, sec_header_flag=True, apid=0x42)
        tc_psc = PacketSeqCtrl(seq_flags=SequenceFlags.UNSEGMENTED, seq_count=22)
        req_id = RequestId(tc_packet_id, tc_psc)
        print(req_id)
        req_id_as_bytes = req_id.pack()
        unpack_req_id = RequestId.unpack(req_id_as_bytes)
        self.assertEqual(unpack_req_id.tc_packet_id.raw(), tc_packet_id.raw())
        self.assertEqual(unpack_req_id.tc_psc.raw(), tc_psc.raw())
        sp_header = SpacePacketHeader.from_composite_fields(
            packet_id=tc_packet_id, psc=tc_psc, data_length=12
        )
        unpack_req_id = RequestId.from_sp_header(sp_header)
        self.assertEqual(unpack_req_id.tc_packet_id.raw(), tc_packet_id.raw())
        self.assertEqual(unpack_req_id.tc_psc.raw(), tc_psc.raw())
        with self.assertRaises(ValueError):
            RequestId.unpack(bytes([0, 1, 2]))

    def test_failure_notice(self):
        error_code = PacketFieldEnum(pfc=8, val=2)
        failure_notice = FailureNotice(code=error_code, data=bytes([0, 2, 4, 8]))
        self.assertEqual(failure_notice.code.val, error_code.val)
        self.assertEqual(failure_notice.code.pfc, error_code.pfc)
        notice_raw = failure_notice.pack()
        notice_unpacked = FailureNotice.unpack(notice_raw, 1, 4)
        self.assertEqual(notice_unpacked.code.val, error_code.val)
        self.assertEqual(notice_unpacked.code.pfc, error_code.pfc)
        self.assertEqual(notice_unpacked.data, bytes([0, 2, 4, 8]))

    def test_verif_params(self):
        sp_header = SpacePacketHeader(
            packet_type=PacketType.TM,
            apid=0x22,
            sec_header_flag=False,
            seq_count=22,
            data_len=35,
        )
        verif_param = VerificationParams(req_id=RequestId.from_sp_header(sp_header))
        self.assertEqual(verif_param.len(), 4)
        verif_param.step_id = StepId(pfc=8, val=12)
        self.assertEqual(verif_param.len(), 5)
        verif_param.step_id.pfc = 16
        self.assertEqual(verif_param.len(), 6)
        verif_param.failure_notice = FailureNotice(
            code=ErrorCode(pfc=16, val=22), data=bytes([0, 1, 2])
        )
        self.assertEqual(verif_param.len(), 11)
