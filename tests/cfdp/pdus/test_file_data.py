from unittest import TestCase

from spacepackets.cfdp import CrcFlag, PduFactory
from spacepackets.cfdp.conf import LargeFileFlag, PduConfig
from spacepackets.cfdp.defs import TransmissionMode
from spacepackets.cfdp.pdu.file_data import (
    FileDataParams,
    FileDataPdu,
    RecordContinuationState,
    SegmentMetadata,
    get_max_file_seg_len_for_max_packet_len_and_pdu_cfg,
)


class TestFileDataPdu(TestCase):
    def setUp(self) -> None:
        self.pdu_conf = PduConfig.default()
        file_data = "hello world"
        self.file_data_bytes = file_data.encode()
        self.fd_params = FileDataParams(
            file_data=self.file_data_bytes, offset=0, segment_metadata=None
        )
        self.pdu = FileDataPdu(pdu_conf=self.pdu_conf, params=self.fd_params)

    def test_max_file_seg_calculator_0(self):
        pdu_conf = PduConfig.default()
        file_seg_len = get_max_file_seg_len_for_max_packet_len_and_pdu_cfg(pdu_conf, 64)
        self.assertEqual(file_seg_len, 53)
        fd_pdu = FileDataPdu(pdu_conf, FileDataParams(b"", 0))
        self.assertEqual(fd_pdu.get_max_file_seg_len_for_max_packet_len(64), 53)

    def test_max_file_seg_calculator_1(self):
        pdu_conf = PduConfig.default()
        pdu_conf.crc_flag = CrcFlag.WITH_CRC
        file_seg_len = get_max_file_seg_len_for_max_packet_len_and_pdu_cfg(pdu_conf, 64)
        self.assertEqual(file_seg_len, 51)
        fd_pdu = FileDataPdu(pdu_conf, FileDataParams(b"", 0))
        self.assertEqual(fd_pdu.get_max_file_seg_len_for_max_packet_len(64), 51)

    def test_max_file_seg_calculator_2(self):
        pdu_conf = PduConfig.default()
        pdu_conf.file_flag = LargeFileFlag.LARGE
        file_seg_len = get_max_file_seg_len_for_max_packet_len_and_pdu_cfg(pdu_conf, 64)
        self.assertEqual(file_seg_len, 49)
        fd_pdu = FileDataPdu(pdu_conf, FileDataParams(b"", 0))
        self.assertEqual(fd_pdu.get_max_file_seg_len_for_max_packet_len(64), 49)

    def test_max_file_seg_calculator_error(self):
        pdu_conf = PduConfig.default()
        file_seg_len = get_max_file_seg_len_for_max_packet_len_and_pdu_cfg(pdu_conf, 11)
        self.assertEqual(file_seg_len, 0)
        with self.assertRaises(ValueError):
            file_seg_len = get_max_file_seg_len_for_max_packet_len_and_pdu_cfg(pdu_conf, 10)
        fd_pdu = FileDataPdu(pdu_conf, FileDataParams(b"", 0))
        with self.assertRaises(ValueError):
            fd_pdu.get_max_file_seg_len_for_max_packet_len(10)

    def test_state(self):
        self.assertEqual(self.pdu.pdu_header.header_len, 7)
        # 15: 'hello world' encoded + 4 bytes offset
        self.assertEqual(self.pdu.packet_len, 7 + 15)
        self.assertEqual(self.pdu.file_data, self.file_data_bytes)
        self.assertEqual(self.pdu.has_segment_metadata, False)
        self.assertEqual(self.pdu.offset, 0)
        self.assertEqual(self.pdu.transmission_mode, TransmissionMode.ACKNOWLEDGED)

    def test_pack_unpack(self):
        file_data_pdu_raw = self.pdu.pack()
        expected_bytes = bytearray([0x30, 0x00, 0x0F, 0x00, 0x00, 0x00, 0x00])
        expected_bytes.extend(bytes([0x00, 0x00, 0x00, 0x00]))
        expected_bytes.extend(self.file_data_bytes)
        self.assertEqual(file_data_pdu_raw, expected_bytes)
        file_data_pdu_unpacked = FileDataPdu.unpack(data=file_data_pdu_raw)
        self.assertEqual(file_data_pdu_unpacked.offset, 0)
        self.assertEqual(file_data_pdu_unpacked.file_data, self.file_data_bytes)

    def test_pack_unpack_w_crc(self):
        pdu_conf = PduConfig.default()
        pdu_conf.crc_flag = CrcFlag.WITH_CRC
        fd_pdu = FileDataPdu(pdu_conf, FileDataParams(self.file_data_bytes, 0))
        packed = fd_pdu.pack()
        expected_bytes = bytearray([0x32, 0x00, 0x11, 0x00, 0x00, 0x00, 0x00])
        expected_bytes.extend(bytes([0x00, 0x00, 0x00, 0x00]))
        expected_bytes.extend(self.file_data_bytes)
        expected_bytes.extend(bytes([0xF6, 0xEB]))  # CRC16
        self.assertEqual(packed, expected_bytes)
        unpacked = FileDataPdu.unpack(packed)
        self.assertEqual(unpacked, fd_pdu)
        self.assertEqual(unpacked.pack(), fd_pdu.pack())

    def test_with_seg_metadata(self):
        fd_params = FileDataParams(
            file_data=self.file_data_bytes,
            offset=0,
            segment_metadata=SegmentMetadata(
                RecordContinuationState.START_AND_END, bytes([0xAA, 0xBB])
            ),
        )
        fd_pdu_with_metadata = FileDataPdu(pdu_conf=self.pdu_conf, params=fd_params)
        expected_packet_len = 7 + 15 + 1 + 2
        self.assertEqual(fd_pdu_with_metadata.packet_len, expected_packet_len)
        fd_pdu_with_metadata_raw = fd_pdu_with_metadata.pack()
        self.assertEqual(len(fd_pdu_with_metadata_raw), expected_packet_len)
        fd_pdu_with_metadata_unpacked = fd_pdu_with_metadata.unpack(data=fd_pdu_with_metadata_raw)
        self.assertEqual(fd_pdu_with_metadata_unpacked.offset, 0)
        self.assertEqual(fd_pdu_with_metadata_unpacked.file_data, self.file_data_bytes)
        self.assertEqual(
            fd_pdu_with_metadata_unpacked.record_cont_state,
            RecordContinuationState.START_AND_END,
        )
        assert fd_pdu_with_metadata.segment_metadata is not None
        self.assertEqual(fd_pdu_with_metadata.segment_metadata.metadata, bytes([0xAA, 0xBB]))

    def test_invalid_metadata(self):
        invalid_metadata = bytes(70)
        with self.assertRaises(ValueError):
            fd_params = FileDataParams(
                file_data=self.file_data_bytes,
                offset=0,
                segment_metadata=SegmentMetadata(
                    RecordContinuationState.START_AND_END, invalid_metadata
                ),
            )
            invalid_pdu = FileDataPdu(pdu_conf=self.pdu_conf, params=fd_params)
            invalid_pdu.pack()

    def test_large_filedata(self):
        fd_params = FileDataParams(
            file_data=self.file_data_bytes,
            offset=0,
            segment_metadata=SegmentMetadata(
                RecordContinuationState.START_AND_END, bytes([0xAA, 0xBB])
            ),
        )
        self.pdu_conf.file_flag = LargeFileFlag.LARGE
        fd_pdu_with_metadata = FileDataPdu(pdu_conf=self.pdu_conf, params=fd_params)
        fd_params = FileDataParams(
            file_data=self.file_data_bytes,
            offset=0,
            segment_metadata=SegmentMetadata(
                RecordContinuationState.START_AND_END, bytes([0xAA, 0xBB])
            ),
        )
        fd_pdu_large_offset = FileDataPdu(pdu_conf=self.pdu_conf, params=fd_params)
        expected_packet_len = 7 + 19 + 1 + 2
        self.assertEqual(fd_pdu_large_offset.packet_len, expected_packet_len)
        fd_pdu_large_offset_raw = fd_pdu_with_metadata.pack()
        self.assertEqual(len(fd_pdu_large_offset_raw), expected_packet_len)
        fd_pdu_large_offset_unpacked = FileDataPdu.unpack(data=fd_pdu_large_offset_raw)
        assert fd_pdu_large_offset_unpacked.segment_metadata is not None
        self.assertEqual(
            fd_pdu_large_offset_unpacked.segment_metadata.metadata, bytes([0xAA, 0xBB])
        )
        self.assertEqual(fd_pdu_large_offset_unpacked.offset, 0)
        fd_pdu_large_offset.file_data = b""
        expected_packet_len -= 11
        self.assertEqual(fd_pdu_large_offset.packet_len, expected_packet_len)
        fd_pdu_large_offset_no_file_data_raw = fd_pdu_large_offset.pack()
        fd_pdu_large_offset_no_file_data_invalid = fd_pdu_large_offset_no_file_data_raw[:-2]
        with self.assertRaises(ValueError):
            FileDataPdu.unpack(data=fd_pdu_large_offset_no_file_data_invalid)
        fd_pdu_large_offset_no_file_data_invalid = fd_pdu_large_offset_no_file_data_raw[:-9]
        with self.assertRaises(ValueError):
            FileDataPdu.unpack(data=fd_pdu_large_offset_no_file_data_invalid)

    def test_with_crc(self):
        self.pdu_conf.crc_flag = CrcFlag.WITH_CRC
        pdu = FileDataPdu(pdu_conf=self.pdu_conf, params=self.fd_params)
        pdu_raw = pdu.pack()
        self.assertEqual(pdu.packet_len, 7 + 15 + 2)
        self.assertEqual(len(pdu_raw), 7 + 15 + 2)

    def test_from_factory(self):
        fd_pdu_raw = self.pdu.pack()
        pdu_holder = PduFactory.from_raw_to_holder(fd_pdu_raw)
        self.assertIsNotNone(pdu_holder.pdu)
        fd_pdu = pdu_holder.to_file_data_pdu()
        self.assertIsNotNone(fd_pdu)
        self.assertEqual(fd_pdu, self.pdu)
