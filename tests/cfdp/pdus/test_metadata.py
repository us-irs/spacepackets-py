from unittest import TestCase

from spacepackets.cfdp import (
    ChecksumType,
    FileStoreRequestTlv,
    FilestoreActionCode,
    ConditionCode,
)
from spacepackets.cfdp.conf import PduConfig
from spacepackets.cfdp.defs import FaultHandlerCode, LargeFileFlag
from spacepackets.cfdp.pdu import MetadataPdu
from spacepackets.cfdp.pdu.metadata import MetadataParams
from spacepackets.cfdp.tlv import TlvHolder, FaultHandlerOverrideTlv


class TestMetadata(TestCase):
    def setUp(self) -> None:
        self.pdu_conf = PduConfig.default()
        self.metadata_params = MetadataParams(
            closure_requested=False,
            file_size=2,
            source_file_name="test.txt",
            dest_file_name="test2.txt",
            checksum_type=ChecksumType.MODULAR,
        )

    def test_metadata_simple(self):
        metadata_pdu = MetadataPdu(pdu_conf=self.pdu_conf, params=self.metadata_params)
        self.check_metadata_fields_0(metadata_pdu=metadata_pdu)
        header_len = metadata_pdu.pdu_file_directive.header_len
        self.assertEqual(header_len, 8)
        # 5 bytes from FSS with normal size and first eight bits
        self.assertEqual(metadata_pdu.packet_len, header_len + 5 + 10 + 9)
        metadata_pdu_raw = metadata_pdu.pack()
        metadata_pdu_unpacked = MetadataPdu.unpack(data=metadata_pdu_raw)
        self.check_metadata_fields_0(metadata_pdu=metadata_pdu_unpacked)
        metadata_pdu_raw = metadata_pdu_raw[: 8 + 6]
        self.assertRaises(ValueError, MetadataPdu.unpack, data=metadata_pdu_raw)

    def test_equal_assertion(self):
        metadata_pdu = MetadataPdu(self.pdu_conf, self.metadata_params)
        metadata_raw = metadata_pdu.pack()
        metadata_unpacked = MetadataPdu.unpack(metadata_raw)
        self.assertEqual(metadata_pdu, metadata_unpacked)

    def test_metadata_pdu(self):
        file_name = "hallo.txt"
        option_0 = FileStoreRequestTlv(
            action_code=FilestoreActionCode.CREATE_FILE_SNM, first_file_name=file_name
        )

        self.assertEqual(option_0.packet_len, 13)
        expected_bytes = bytearray()
        expected_bytes.extend(bytes([0x00, 0x0B, 0x00, 0x09]))
        expected_bytes.extend(file_name.encode())
        self.assertEqual(option_0.pack(), expected_bytes)

        # Create completey new packet
        pdu_with_option = MetadataPdu(
            pdu_conf=self.pdu_conf,
            params=self.metadata_params,
            options=[option_0],
        )
        header_len = pdu_with_option.pdu_file_directive.header_len
        self.assertEqual(pdu_with_option.options, [option_0])
        expected_len = 10 + 9 + 8 + 5 + 13
        self.assertEqual(pdu_with_option.packet_len, expected_len)
        pdu_with_option_raw = pdu_with_option.pack()
        self.assertEqual(len(pdu_with_option_raw), expected_len)
        pdu_with_option_unpacked = MetadataPdu.unpack(data=pdu_with_option_raw)
        tlv_wrapper = TlvHolder(pdu_with_option_unpacked.options[0])
        tlv_typed = tlv_wrapper.to_fs_request()
        self.assertIsNotNone(tlv_typed)
        self.assertEqual(tlv_typed.pack(), option_0.pack())

        pdu_with_option.source_file_name = None
        pdu_with_option.dest_file_name = None
        expected_len = header_len + 1 + 1 + 5 + 13
        self.assertEqual(pdu_with_option.directive_param_field_len, 1 + 1 + 5 + 13)
        self.assertEqual(pdu_with_option.packet_len, expected_len)

        option_1 = FaultHandlerOverrideTlv(
            condition_code=ConditionCode.POSITIVE_ACK_LIMIT_REACHED,
            handler_code=FaultHandlerCode.ABANDON_TRANSACTION,
        )
        self.assertEqual(option_1.packet_len, 3)
        metadata_params = MetadataParams(
            closure_requested=False,
            file_size=2,
            source_file_name=None,
            dest_file_name=None,
            checksum_type=ChecksumType.MODULAR,
        )
        pdu_with_two_options = MetadataPdu(
            pdu_conf=self.pdu_conf,
            params=metadata_params,
            options=[option_0, option_1],
        )
        pdu_with_two_options_raw = pdu_with_two_options.pack()
        expected_len = header_len + 5 + 2 + option_0.packet_len + option_1.packet_len
        self.assertEqual(pdu_with_two_options.packet_len, expected_len)
        self.assertEqual(len(pdu_with_two_options_raw), expected_len)
        pdu_with_two_options.source_file_name = "hello.txt"
        expected_len = (
            header_len + 5 + 1 + 10 + option_0.packet_len + option_1.packet_len
        )
        self.assertEqual(pdu_with_two_options.packet_len, expected_len)
        pdu_with_two_options.dest_file_name = "hello2.txt"
        expected_len = (
            header_len + 5 + 11 + 10 + option_0.packet_len + option_1.packet_len
        )
        self.assertEqual(pdu_with_two_options.packet_len, expected_len)
        pdu_with_no_options = pdu_with_two_options
        pdu_with_no_options.options = None
        pdu_with_no_options.params.file_size = pow(2, 32) + 1
        with self.assertRaises(ValueError):
            pdu_with_no_options.pack()

        self.pdu_conf.file_flag = LargeFileFlag.LARGE
        pdu_file_size_large = MetadataPdu(
            pdu_conf=self.pdu_conf,
            params=metadata_params,
            options=None,
        )
        self.assertEqual(pdu_file_size_large.pdu_file_directive.header_len, header_len)
        self.assertEqual(pdu_file_size_large.packet_len, header_len + 2 + 9)
        pdu_file_size_large.options = [option_0]
        pdu_file_size_large_raw = pdu_file_size_large.pack()
        pdu_file_size_large_raw = pdu_file_size_large_raw[:-2]
        with self.assertRaises(ValueError):
            MetadataPdu.unpack(data=pdu_file_size_large_raw)

    def check_metadata_fields_0(self, metadata_pdu: MetadataPdu):
        self.assertEqual(metadata_pdu.params.closure_requested, False)
        self.assertEqual(metadata_pdu.params.file_size, 2)
        self.assertEqual(metadata_pdu.source_file_name, "test.txt")
        self.assertEqual(metadata_pdu.dest_file_name, "test2.txt")
        self.assertEqual(metadata_pdu.pdu_file_directive.header_len, 8)
        self.assertEqual(metadata_pdu._source_file_name_lv.packet_len, 9)
        self.assertEqual(metadata_pdu._dest_file_name_lv.packet_len, 10)
