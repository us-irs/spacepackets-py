from unittest import TestCase
from spacepackets.cfdp.pdu.ack import AckPdu, ConditionCode, DirectiveCodes, TransactionStatus, \
    TransmissionModes, CrcFlag
from spacepackets.util import get_printable_data_string, PrintFormats


class TestPdus(TestCase):

    def test_ack_pdu(self):
        ack_pdu = AckPdu(
            directive_code_of_acked_pdu=DirectiveCodes.FINISHED_PDU,
            condition_code_of_acked_pdu=ConditionCode.NO_ERROR,
            transaction_status=TransactionStatus.TERMINATED,
            transaction_seq_num=bytes([0x00, 0x01]),
            source_entity_id=bytes([0x00, 0x00]),
            dest_entity_id=bytes([0x00, 0x01]),
            crc_flag=CrcFlag.NO_CRC,
            trans_mode=TransmissionModes.ACKNOWLEDGED
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

        ack_pdu_2 = AckPdu(
            directive_code_of_acked_pdu=DirectiveCodes.EOF_PDU,
            condition_code_of_acked_pdu=ConditionCode.POSITIVE_ACK_LIMIT_REACHED,
            transaction_status=TransactionStatus.ACTIVE,
            transaction_seq_num=bytes([0x50, 0x00, 0x10, 0x01]),
            source_entity_id=bytes([0x10, 0x00, 0x01, 0x02]),
            dest_entity_id=bytes([0x30, 0x00, 0x01, 0x03]),
            crc_flag=CrcFlag.WITH_CRC,
            trans_mode=TransmissionModes.UNACKNOWLEDGED
        )
        self.check_fields_packet_1(ack_pdu=ack_pdu_2)
        ack_pdu_raw = ack_pdu_2.pack()
        self.assertEqual(len(ack_pdu_raw), 19)
        print(ack_pdu_raw.hex(sep=','))
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

        self.assertRaises(
            ValueError, AckPdu,
            directive_code_of_acked_pdu=DirectiveCodes.NAK_PDU,
            condition_code_of_acked_pdu=ConditionCode.POSITIVE_ACK_LIMIT_REACHED,
            transaction_status=TransactionStatus.ACTIVE,
            transaction_seq_num=bytes([0x50, 0x00, 0x10, 0x01]),
            source_entity_id=bytes([0x10, 0x00, 0x01, 0x02]),
            dest_entity_id=bytes([0x30, 0x00, 0x01, 0x03]),
            crc_flag=CrcFlag.WITH_CRC,
            trans_mode=TransmissionModes.UNACKNOWLEDGED
        )

    def check_fields_packet_0(self, ack_pdu: AckPdu):
        self.assertEqual(ack_pdu.directive_code_of_acked_pdu, DirectiveCodes.FINISHED_PDU)
        self.assertEqual(ack_pdu.condition_code_of_acked_pdu, ConditionCode.NO_ERROR)
        self.assertEqual(ack_pdu.transaction_status, TransactionStatus.TERMINATED)
        self.assertEqual(
            ack_pdu.pdu_file_directive.pdu_header.transaction_seq_num, bytes([0x00, 0x01])
        )
        self.assertEqual(
            ack_pdu.pdu_file_directive.pdu_header.source_entity_id, bytes([0x00, 0x00])
        )
        self.assertEqual(
            ack_pdu.pdu_file_directive.pdu_header.dest_entity_id, bytes([0x00, 0x01])
        )
        self.assertEqual(
            ack_pdu.pdu_file_directive.pdu_header.trans_mode, TransmissionModes.ACKNOWLEDGED
        )
        self.assertEqual(ack_pdu.get_packed_len(), 13)

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
            ack_pdu.pdu_file_directive.pdu_header.source_entity_id, bytes([0x10, 0x00, 0x01, 0x02])
        )
        self.assertEqual(
            ack_pdu.pdu_file_directive.pdu_header.dest_entity_id, bytes([0x30, 0x00, 0x01, 0x03])
        )
        self.assertEqual(
            ack_pdu.pdu_file_directive.pdu_header.trans_mode, TransmissionModes.UNACKNOWLEDGED
        )
        self.assertEqual(ack_pdu.get_packed_len(), 19)
