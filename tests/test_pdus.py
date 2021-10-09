from unittest import TestCase
from spacepackets.cfdp.pdu.ack import AckPdu, ConditionCode, DirectiveCodes, TransactionStatus, \
    CrcFlag
from spacepackets.cfdp.conf import PduConfig, TransmissionModes, Direction, FileSize
from spacepackets.cfdp.pdu.nak import NakPdu
from spacepackets.util import get_printable_data_string, PrintFormats


class TestPdus(TestCase):

    def test_ack_pdu(self):
        pdu_conf = PduConfig(
            transaction_seq_num=bytes([0x00, 0x01]),
            source_entity_id=bytes([0x00, 0x00]),
            dest_entity_id=bytes([0x00, 0x01]),
            crc_flag=CrcFlag.NO_CRC,
            trans_mode=TransmissionModes.ACKNOWLEDGED
        )
        ack_pdu = AckPdu(
            directive_code_of_acked_pdu=DirectiveCodes.FINISHED_PDU,
            condition_code_of_acked_pdu=ConditionCode.NO_ERROR,
            transaction_status=TransactionStatus.TERMINATED,
            pdu_conf=pdu_conf
        )
        self.check_fields_packet_0(ack_pdu=ack_pdu)
        ack_pdu_raw = ack_pdu.pack()
        self.assertEqual(len(ack_pdu_raw), 13)
        self.assertEqual(
            ack_pdu_raw,
            # 0x06 because this is the directive code of ACK PDUs
            # 0x51 because 0x05 << 4 is the directive code of the Finished PDU and 0b0001 because
            # because this is the value of finished PDUs
            # 0x02 because this is the terminated transaction status
            bytes([0x20, 0x00, 0x03, 0x22, 0x00, 0x00, 0x00, 0x01, 0x00, 0x01, 0x06, 0x51, 0x02])
        )
        ack_pdu_unpacked = AckPdu.unpack(raw_packet=ack_pdu_raw)
        self.check_fields_packet_0(ack_pdu=ack_pdu_unpacked)

        pdu_conf = PduConfig(
            transaction_seq_num=bytes([0x50, 0x00, 0x10, 0x01]),
            source_entity_id=bytes([0x10, 0x00, 0x01, 0x02]),
            dest_entity_id=bytes([0x30, 0x00, 0x01, 0x03]),
            crc_flag=CrcFlag.WITH_CRC,
            trans_mode=TransmissionModes.UNACKNOWLEDGED
        )
        ack_pdu_2 = AckPdu(
            directive_code_of_acked_pdu=DirectiveCodes.EOF_PDU,
            condition_code_of_acked_pdu=ConditionCode.POSITIVE_ACK_LIMIT_REACHED,
            transaction_status=TransactionStatus.ACTIVE,
            pdu_conf=pdu_conf
        )
        self.check_fields_packet_1(ack_pdu=ack_pdu_2)
        ack_pdu_raw = ack_pdu_2.pack()
        self.assertEqual(len(ack_pdu_raw), 19)
        self.assertEqual(
            ack_pdu_raw,
            # 0x06 because this is the directive code of ACK PDUs
            # 0x40 because 0x04 << 4 is the directive code of the EOF PDU and 0b0000 because
            # because this is not a Finished PDUs
            # 0x11 because this has the Active transaction status and the condition code is the
            # Positive Ack Limit Reached Condition Code
            bytes([
                0x26, 0x00, 0x03, 0x44,
                0x10, 0x00, 0x01, 0x02,
                0x50, 0x00, 0x10, 0x01,
                0x30, 0x00, 0x01, 0x03,
                0x06, 0x40, 0x11
            ])
        )
        # Invalid directive code
        pdu_conf = PduConfig.empty()
        self.assertRaises(
            ValueError, AckPdu,
            directive_code_of_acked_pdu=DirectiveCodes.NAK_PDU,
            condition_code_of_acked_pdu=ConditionCode.POSITIVE_ACK_LIMIT_REACHED,
            transaction_status=TransactionStatus.ACTIVE,
            pdu_conf=pdu_conf
        )

    def check_fields_packet_0(self, ack_pdu: AckPdu):
        self.assertEqual(ack_pdu.directive_code_of_acked_pdu, DirectiveCodes.FINISHED_PDU)
        self.assertEqual(ack_pdu.condition_code_of_acked_pdu, ConditionCode.NO_ERROR)
        self.assertEqual(ack_pdu.transaction_status, TransactionStatus.TERMINATED)
        self.assertEqual(
            ack_pdu.pdu_file_directive.pdu_header.pdu_conf.transaction_seq_num, bytes([0x00, 0x01])
        )
        self.assertEqual(
            ack_pdu.pdu_file_directive.pdu_header.pdu_conf.source_entity_id, bytes([0x00, 0x00])
        )
        self.assertEqual(
            ack_pdu.pdu_file_directive.pdu_header.pdu_conf.dest_entity_id, bytes([0x00, 0x01])
        )
        self.assertEqual(
            ack_pdu.pdu_file_directive.pdu_header.pdu_conf.trans_mode,
            TransmissionModes.ACKNOWLEDGED
        )
        self.assertEqual(ack_pdu.packed_len, 13)

    def check_fields_packet_1(self, ack_pdu: AckPdu):
        self.assertEqual(ack_pdu.directive_code_of_acked_pdu, DirectiveCodes.EOF_PDU)
        self.assertEqual(
            ack_pdu.condition_code_of_acked_pdu, ConditionCode.POSITIVE_ACK_LIMIT_REACHED
        )
        self.assertEqual(ack_pdu.transaction_status, TransactionStatus.ACTIVE)
        self.assertEqual(
            ack_pdu.pdu_file_directive.pdu_header.transaction_seq_num,
            bytes([0x50, 0x00, 0x10, 0x01])
        )
        self.assertEqual(
            ack_pdu.pdu_file_directive.pdu_header.pdu_conf.source_entity_id,
            bytes([0x10, 0x00, 0x01, 0x02])
        )
        self.assertEqual(
            ack_pdu.pdu_file_directive.pdu_header.pdu_conf.dest_entity_id,
            bytes([0x30, 0x00, 0x01, 0x03])
        )
        self.assertEqual(
            ack_pdu.pdu_file_directive.pdu_header.pdu_conf.trans_mode,
            TransmissionModes.UNACKNOWLEDGED
        )
        self.assertEqual(ack_pdu.packed_len, 19)

    def test_nak_pdu(self):
        pdu_conf = PduConfig(
            trans_mode=TransmissionModes.ACKNOWLEDGED,
            transaction_seq_num=bytes([0x00, 0x01]),
            source_entity_id=bytes([0x00, 0x00]),
            dest_entity_id=bytes([0x00, 0x01])
        )
        nak_pdu = NakPdu(
            start_of_scope=0,
            end_of_scope=200,
            pdu_conf=pdu_conf
        )
        self.assertEqual(nak_pdu.segment_requests, [])
        pdu_header = nak_pdu.pdu_file_directive.pdu_header
        self.assertEqual(pdu_header.direction, Direction.TOWARDS_RECEIVER)
        # Start of scope (4) + end of scope (4) + directive code
        self.assertEqual(pdu_header.pdu_data_field_len, 8 + 1)
        self.assertEqual(pdu_header.file_size, FileSize.NORMAL)
        self.assertEqual(pdu_header.trans_mode, TransmissionModes.ACKNOWLEDGED)
        self.assertEqual(nak_pdu.file_size, FileSize.NORMAL)
        self.assertEqual(nak_pdu.packet_len, 19)
        nak_packed = nak_pdu.pack()
        self.assertEqual(len(nak_packed), 19)
        nak_pdu.file_size = FileSize.LARGE
        self.assertEqual(pdu_header.file_size, FileSize.LARGE)
        self.assertEqual(nak_pdu.file_size, FileSize.LARGE)
        self.assertEqual(nak_pdu.packet_len, 27)
        nak_packed = nak_pdu.pack()
        self.assertEqual(len(nak_packed), 27)

        nak_pdu.file_size = FileSize.NORMAL
        self.assertEqual(pdu_header.file_size, FileSize.NORMAL)
        self.assertEqual(nak_pdu.file_size, FileSize.NORMAL)
        self.assertEqual(nak_pdu.packet_len, 19)
        nak_packed = nak_pdu.pack()
        self.assertEqual(len(nak_packed), 19)

        nak_pdu.start_of_scope = pow(2, 32) + 1
        nak_pdu.end_of_scope = pow(2, 32) + 1
        self.assertRaises(ValueError, nak_pdu.pack)

        nak_pdu.start_of_scope = 0
        nak_pdu.end_of_scope = 200
        segment_requests = [(20, 40), (60, 80)]
        nak_pdu.segment_requests = segment_requests
        self.assertEqual(nak_pdu.segment_requests, segment_requests)
        # Additional 2 segment requests, each has size 8
        self.assertEqual(nak_pdu.packet_len, 35)
        nak_packed = nak_pdu.pack()
        self.assertEqual(len(nak_packed), 35)
        nak_unpacked = NakPdu.unpack(raw_packet=nak_packed)
        self.assertEqual(nak_unpacked.pack(), nak_packed)

        nak_pdu.file_size = FileSize.LARGE
        # 2 segment requests with size 16 each plus 16 for start and end of scope
        self.assertEqual(nak_pdu.pdu_file_directive.pdu_header.header_len, 10)
        self.assertEqual(nak_pdu.pdu_file_directive.header_len, 11)
        self.assertEqual(nak_pdu.packet_len, 11 + 48)
        nak_packed = nak_pdu.pack()
        self.assertEqual(len(nak_packed), 59)
        nak_repacked = nak_unpacked.pack()
        nak_unpacked = NakPdu.unpack(raw_packet=nak_packed)
        self.assertEqual(nak_unpacked.pack(), nak_packed)
        nak_repacked.append(0)
        self.assertRaises(ValueError, NakPdu.unpack, raw_packet=nak_repacked)
        nak_pdu.segment_requests = []
        self.assertEqual(nak_pdu.packet_len, 59 - 32)
        nak_packed = nak_pdu.pack()
        self.assertEqual(len(nak_packed), 59 - 32)

        nak_pdu.file_size = FileSize.NORMAL
        segment_requests = [(pow(2, 32) + 1, 40), (60, 80)]
        nak_pdu.segment_requests = segment_requests
        self.assertRaises(ValueError, nak_pdu.pack)

    def test_finished_pdu(self):
        pass

    def test_keep_alive_pdu(self):
        pass

    def test_metadata_pdu(self):
        pass

    def test_prompt_pdu(self):
        pass
