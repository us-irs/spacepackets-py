from unittest import TestCase

from spacepackets.cfdp import (
    NULL_CHECKSUM_U32,
    ConditionCode,
    PduConfig,
    DirectiveType,
    ChecksumType,
)
from spacepackets.cfdp.pdu import (
    EofPdu,
    PduFactory,
    FileDataPdu,
    MetadataPdu,
    MetadataParams,
    AckPdu,
    TransactionStatus,
    NakPdu,
)
from spacepackets.cfdp.pdu.file_data import FileDataParams
from spacepackets.cfdp.pdu.finished import (
    FinishedParams,
    DeliveryCode,
    FileDeliveryStatus,
    FinishedPdu,
)
from spacepackets.cfdp.pdu.prompt import ResponseRequired, PromptPdu


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

    def test_metadata_pdu_creation(self):
        pdu_conf = PduConfig.default()
        metadata_params = MetadataParams(
            closure_requested=False,
            file_size=2,
            source_file_name="test.txt",
            dest_file_name="test2.txt",
            checksum_type=ChecksumType.MODULAR,
        )
        metadata_pdu = MetadataPdu(pdu_conf, metadata_params)
        metadata_raw = metadata_pdu.pack()
        metadata_pdu_from_factory = PduFactory.from_raw(metadata_raw)
        self.assertEqual(metadata_pdu, metadata_pdu_from_factory)

    def test_eof_pdu_creation(self):
        eof_pdu = EofPdu(
            file_checksum=NULL_CHECKSUM_U32, file_size=0, pdu_conf=self.pdu_conf
        )
        eof_raw = eof_pdu.pack()
        eof_unpacked = EofPdu.unpack(eof_raw)
        self.assertEqual(eof_pdu, eof_unpacked)

    def test_finished_pdu_creation(self):
        params = FinishedParams(
            delivery_code=DeliveryCode.DATA_COMPLETE,
            delivery_status=FileDeliveryStatus.FILE_STATUS_UNREPORTED,
            condition_code=ConditionCode.NO_ERROR,
        )
        finish_pdu = FinishedPdu(
            params=params,
            pdu_conf=self.pdu_conf,
        )
        finished_raw = finish_pdu.pack()
        finished_unpacked = FinishedPdu.unpack(finished_raw)
        self.assertEqual(finished_unpacked, finish_pdu)

    def test_file_data_pdu_creation(self):
        file_data = "hello world"
        file_data_bytes = file_data.encode()
        fd_params = FileDataParams(
            file_data=file_data_bytes, offset=0, segment_metadata_flag=False
        )

        file_data_pdu = FileDataPdu(pdu_conf=self.pdu_conf, params=fd_params)
        fd_raw = file_data_pdu.pack()
        fd_unpacked = FileDataPdu.unpack(fd_raw)
        self.assertEqual(file_data_pdu, fd_unpacked)

    def test_ack_pdu_creation(self):
        ack_pdu = AckPdu(
            directive_code_of_acked_pdu=DirectiveType.FINISHED_PDU,
            condition_code_of_acked_pdu=ConditionCode.NO_ERROR,
            transaction_status=TransactionStatus.TERMINATED,
            pdu_conf=self.pdu_conf,
        )
        ack_raw = ack_pdu.pack()
        ack_unpacked = AckPdu.unpack(ack_raw)
        self.assertEqual(ack_pdu, ack_unpacked)

    def test_nak_pdu_creation(self):
        nak_pdu = NakPdu(start_of_scope=0, end_of_scope=200, pdu_conf=self.pdu_conf)
        nak_raw = nak_pdu.pack()
        nak_unpacked = NakPdu.unpack(nak_raw)
        self.assertEqual(nak_pdu, nak_unpacked)

    def test_prompt_pdu_creation(self):
        prompt_pdu = PromptPdu(
            pdu_conf=self.pdu_conf, response_required=ResponseRequired.KEEP_ALIVE
        )
        prompt_raw = prompt_pdu.pack()
        prompt_unpacked = PromptPdu.unpack(prompt_raw)
        self.assertEqual(prompt_pdu, prompt_unpacked)
