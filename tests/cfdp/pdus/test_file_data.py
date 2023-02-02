from unittest import TestCase
from spacepackets.cfdp.pdu.file_data import (
    FileDataPdu,
    SegmentMetadataFlag,
    RecordContinuationState,
    FileDataParams,
)
from spacepackets.cfdp.conf import PduConfig, LargeFileFlag


class TestFileDataPdu(TestCase):
    def test_file_data_pdu(self):
        pdu_conf = PduConfig.default()
        file_data = "hello world"
        file_data_bytes = file_data.encode()
        fd_params = FileDataParams(
            file_data=file_data_bytes, offset=0, segment_metadata_flag=False
        )

        file_data_pdu = FileDataPdu(pdu_conf=pdu_conf, params=fd_params)
        self.assertEqual(file_data_pdu.pdu_header.header_len, 7)
        # 15: 'hello world' encoded + 4 bytes offset
        self.assertEqual(file_data_pdu.packet_len, 7 + 15)
        self.assertEqual(file_data_pdu.file_data, file_data_bytes)
        self.assertEqual(file_data_pdu.has_segment_metadata, False)
        self.assertEqual(file_data_pdu.offset, 0)
        file_data_pdu_raw = file_data_pdu.pack()
        expected_bytes = bytearray([0x30, 0x00, 0x0F, 0x11, 0x00, 0x00, 0x00])
        expected_bytes.extend(bytes([0x00, 0x00, 0x00, 0x00]))
        expected_bytes.extend(file_data_bytes)
        self.assertEqual(file_data_pdu_raw, expected_bytes)
        file_data_pdu_unpacked = FileDataPdu.unpack(data=file_data_pdu_raw)
        self.assertEqual(file_data_pdu_unpacked.offset, 0)
        self.assertEqual(file_data_pdu_unpacked.file_data, file_data_bytes)

        fd_params = FileDataParams(
            file_data=file_data_bytes,
            offset=0,
            segment_metadata_flag=SegmentMetadataFlag.PRESENT,
            record_cont_state=RecordContinuationState.START_AND_END,
            segment_metadata=bytes([0xAA, 0xBB]),
        )
        fd_pdu_with_metadata = FileDataPdu(pdu_conf=pdu_conf, params=fd_params)
        expected_packet_len = 7 + 15 + 1 + 2
        self.assertEqual(fd_pdu_with_metadata.packet_len, expected_packet_len)
        fd_pdu_with_metadata_raw = fd_pdu_with_metadata.pack()
        self.assertEqual(len(fd_pdu_with_metadata_raw), expected_packet_len)
        fd_pdu_with_metadata_unpacked = fd_pdu_with_metadata.unpack(
            data=fd_pdu_with_metadata_raw
        )
        self.assertEqual(fd_pdu_with_metadata_unpacked.offset, 0)
        self.assertEqual(fd_pdu_with_metadata_unpacked.file_data, file_data_bytes)
        self.assertEqual(
            fd_pdu_with_metadata_unpacked.record_cont_state,
            RecordContinuationState.START_AND_END,
        )
        self.assertEqual(fd_pdu_with_metadata.segment_metadata, bytes([0xAA, 0xBB]))
        invalid_metadata = bytes(70)
        with self.assertRaises(ValueError):
            fd_params = FileDataParams(
                file_data=file_data_bytes,
                offset=0,
                segment_metadata_flag=SegmentMetadataFlag.PRESENT,
                record_cont_state=RecordContinuationState.START_AND_END,
                segment_metadata=invalid_metadata,
            )
            invalid_pdu = FileDataPdu(pdu_conf=pdu_conf, params=fd_params)
            invalid_pdu.pack()

        pdu_conf.file_flag = LargeFileFlag.LARGE

        fd_params = FileDataParams(
            file_data=file_data_bytes,
            offset=0,
            segment_metadata_flag=SegmentMetadataFlag.PRESENT,
            record_cont_state=RecordContinuationState.START_AND_END,
            segment_metadata=bytes([0xAA, 0xBB]),
        )
        fd_pdu_large_offset = FileDataPdu(pdu_conf=pdu_conf, params=fd_params)
        expected_packet_len = 7 + 19 + 1 + 2
        self.assertEqual(fd_pdu_large_offset.packet_len, expected_packet_len)
        fd_pdu_large_offset_raw = fd_pdu_with_metadata.pack()
        self.assertEqual(len(fd_pdu_large_offset_raw), expected_packet_len)
        fd_pdu_large_offset_unpacked = FileDataPdu.unpack(data=fd_pdu_large_offset_raw)
        self.assertEqual(
            fd_pdu_large_offset_unpacked.segment_metadata, bytes([0xAA, 0xBB])
        )
        self.assertEqual(fd_pdu_large_offset_unpacked.offset, 0)
        fd_pdu_large_offset.file_data = bytes()
        expected_packet_len -= 11
        self.assertEqual(fd_pdu_large_offset.packet_len, expected_packet_len)
        fd_pdu_large_offset_no_file_data_raw = fd_pdu_large_offset.pack()
        fd_pdu_large_offset_no_file_data_invalid = fd_pdu_large_offset_no_file_data_raw[
            :-2
        ]
        with self.assertRaises(ValueError):
            FileDataPdu.unpack(data=fd_pdu_large_offset_no_file_data_invalid)
        fd_pdu_large_offset_no_file_data_invalid = fd_pdu_large_offset_no_file_data_raw[
            :-9
        ]
        with self.assertRaises(ValueError):
            FileDataPdu.unpack(data=fd_pdu_large_offset_no_file_data_invalid)
