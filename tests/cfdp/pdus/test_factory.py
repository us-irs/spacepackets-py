from unittest import TestCase

from spacepackets.cfdp import (
    NULL_CHECKSUM_U32,
    ConditionCode,
    PduConfig,
    DirectiveType,
    ChecksumTypes,
)
from spacepackets.cfdp.pdu import (
    EofPdu,
    PduFactory,
    FileDataPdu,
    MetadataPdu,
    MetadataParams,
)
from spacepackets.cfdp.pdu.file_data import FileDataParams


class TestPduHolder(TestCase):
    def setUp(self) -> None:
        self.pdu_conf = PduConfig.default()
        self.pdu_factory = PduFactory()

    def test_factory_file_directive_getter(self):
        eof_pdu = EofPdu(
            file_checksum=NULL_CHECKSUM_U32,
            condition_code=ConditionCode.NO_ERROR,
            file_size=0,
            pdu_conf=self.pdu_conf,
        )
        eof_raw = eof_pdu.pack()
        self.assertEqual(
            self.pdu_factory.pdu_directive_type(eof_raw), DirectiveType.EOF_PDU
        )

    def test_factory_file_directive_on_file_data(self):
        fd_params = FileDataParams(file_data=bytes(), offset=0)
        file_data_pdu = FileDataPdu(fd_params, self.pdu_conf)
        fd_pdu_raw = file_data_pdu.pack()
        self.assertEqual(self.pdu_factory.pdu_directive_type(fd_pdu_raw), None)

    def test_factory_metadata_pdu(self):
        pdu_conf = PduConfig.default()
        metadata_params = MetadataParams(
            closure_requested=False,
            file_size=2,
            source_file_name="test.txt",
            dest_file_name="test2.txt",
            checksum_type=ChecksumTypes.MODULAR,
        )
        metadata_pdu = MetadataPdu(pdu_conf, metadata_params)
        metadata_raw = metadata_pdu.pack()
        metadata_pdu_from_factory = PduFactory.from_raw(metadata_raw)
        self.assertEqual(metadata_pdu, metadata_pdu_from_factory)
