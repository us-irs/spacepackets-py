from unittest import TestCase

from spacepackets.cfdp import ChecksumTypes
from spacepackets.cfdp.conf import PduConfig
from spacepackets.cfdp.pdu import MetadataPdu
from spacepackets.cfdp.pdu.file_data import FileDataPdu
from spacepackets.cfdp.pdu.wrapper import PduWrapper


class TestPduWrapper(TestCase):
    def setUp(self) -> None:
        self.pdu_conf = PduConfig.empty()
        self.file_data = "hello world"
        self.file_data_bytes = self.file_data.encode()
        self.pdu_wrapper = PduWrapper(None)

    def test_file_data(self):
        file_data_pdu = FileDataPdu(
            pdu_conf=self.pdu_conf,
            file_data=self.file_data_bytes,
            offset=0,
            segment_metadata_flag=False,
        )
        self.pdu_wrapper.base = file_data_pdu
        pdu_casted_back = self.pdu_wrapper.to_file_data_pdu()
        self.assertEqual(pdu_casted_back, file_data_pdu)

    def test_invalid_to_file_data(self):
        metadata_pdu = MetadataPdu(
            pdu_conf=self.pdu_conf,
            closure_requested=False,
            file_size=2,
            source_file_name="test.txt",
            dest_file_name="test2.txt",
            checksum_type=ChecksumTypes.MODULAR,
        )
        self.pdu_wrapper.base = metadata_pdu
        with self.assertRaises(TypeError) as cm:
            self.pdu_wrapper.to_file_data_pdu()
        exception = cm.exception
        self.assertIn("Stored PDU is not 'FileDataPdu'", str(exception))

    def test_metadata(self):
        metadata_pdu = MetadataPdu(
            pdu_conf=self.pdu_conf,
            closure_requested=False,
            file_size=2,
            source_file_name="test.txt",
            dest_file_name="test2.txt",
            checksum_type=ChecksumTypes.MODULAR,
        )
        self.pdu_wrapper.base = metadata_pdu
        metadata_casted_back = self.pdu_wrapper.to_metadata_pdu()
        self.assertEqual(metadata_casted_back, metadata_pdu)

    def test_invalid_cast(self):
        file_data_pdu = FileDataPdu(
            pdu_conf=self.pdu_conf,
            file_data=self.file_data_bytes,
            offset=0,
            segment_metadata_flag=False,
        )
        self.pdu_wrapper.base = file_data_pdu
        with self.assertRaises(TypeError) as cm:
            self.pdu_wrapper.to_metadata_pdu()
        exception = cm.exception
        self.assertTrue("Stored PDU is not 'MetadataPdu'" in str(exception))
