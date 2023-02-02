from unittest import TestCase

from spacepackets.cfdp import CrcFlag, TransmissionMode, LargeFileFlag, ConditionCode
from spacepackets.cfdp.conf import PduConfig
from spacepackets.cfdp.pdu import AckPdu, DirectiveType, TransactionStatus
from spacepackets.util import ByteFieldU16, ByteFieldU32


class TestAckPdu(TestCase):
    def test_ack_pdu(self):
        pdu_conf = PduConfig(
            transaction_seq_num=ByteFieldU16(1),
            source_entity_id=ByteFieldU16(2),
            dest_entity_id=ByteFieldU16(3),
            crc_flag=CrcFlag.NO_CRC,
            trans_mode=TransmissionMode.ACKNOWLEDGED,
            file_flag=LargeFileFlag.NORMAL,
        )
        ack_pdu = AckPdu(
            directive_code_of_acked_pdu=DirectiveType.FINISHED_PDU,
            condition_code_of_acked_pdu=ConditionCode.NO_ERROR,
            transaction_status=TransactionStatus.TERMINATED,
            pdu_conf=pdu_conf,
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
            bytes(
                [
                    0x20,
                    0x00,
                    0x03,
                    0x22,
                    0x00,  # This and following byte in source ID
                    0x02,
                    0x00,  # This and following byte is seq number
                    0x01,
                    0x00,  # This and following byte in dest ID
                    0x03,
                    0x06,
                    0x51,
                    0x02,
                ]
            ),
        )
        ack_pdu_unpacked = AckPdu.unpack(data=ack_pdu_raw)
        self.check_fields_packet_0(ack_pdu=ack_pdu_unpacked)

        pdu_conf = PduConfig(
            transaction_seq_num=ByteFieldU32.from_bytes(
                bytes([0x50, 0x00, 0x10, 0x01])
            ),
            source_entity_id=ByteFieldU32.from_bytes(bytes([0x10, 0x00, 0x01, 0x02])),
            dest_entity_id=ByteFieldU32.from_bytes(bytes([0x30, 0x00, 0x01, 0x03])),
            crc_flag=CrcFlag.WITH_CRC,
            trans_mode=TransmissionMode.UNACKNOWLEDGED,
            file_flag=LargeFileFlag.NORMAL,
        )
        ack_pdu_2 = AckPdu(
            directive_code_of_acked_pdu=DirectiveType.EOF_PDU,
            condition_code_of_acked_pdu=ConditionCode.POSITIVE_ACK_LIMIT_REACHED,
            transaction_status=TransactionStatus.ACTIVE,
            pdu_conf=pdu_conf,
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
            bytes(
                [
                    0x26,
                    0x00,
                    0x03,
                    0x44,
                    0x10,
                    0x00,
                    0x01,
                    0x02,
                    0x50,
                    0x00,
                    0x10,
                    0x01,
                    0x30,
                    0x00,
                    0x01,
                    0x03,
                    0x06,
                    0x40,
                    0x11,
                ]
            ),
        )
        # Invalid directive code
        pdu_conf = PduConfig.empty()
        self.assertRaises(
            ValueError,
            AckPdu,
            directive_code_of_acked_pdu=DirectiveType.NAK_PDU,
            condition_code_of_acked_pdu=ConditionCode.POSITIVE_ACK_LIMIT_REACHED,
            transaction_status=TransactionStatus.ACTIVE,
            pdu_conf=pdu_conf,
        )

    def check_fields_packet_0(self, ack_pdu: AckPdu):
        self.assertEqual(
            ack_pdu.directive_code_of_acked_pdu, DirectiveType.FINISHED_PDU
        )
        self.assertEqual(ack_pdu.condition_code_of_acked_pdu, ConditionCode.NO_ERROR)
        self.assertEqual(ack_pdu.transaction_status, TransactionStatus.TERMINATED)
        self.assertEqual(
            ack_pdu.pdu_file_directive.pdu_header.pdu_conf.transaction_seq_num,
            ByteFieldU16(1),
        )
        self.assertEqual(
            ack_pdu.pdu_file_directive.pdu_header.pdu_conf.source_entity_id,
            ByteFieldU16(2),
        )
        self.assertEqual(
            ack_pdu.pdu_file_directive.pdu_header.pdu_conf.dest_entity_id,
            ByteFieldU16(3),
        )
        self.assertEqual(
            ack_pdu.pdu_file_directive.pdu_header.pdu_conf.trans_mode,
            TransmissionMode.ACKNOWLEDGED,
        )
        self.assertEqual(ack_pdu.packet_len, 13)

    def check_fields_packet_1(self, ack_pdu: AckPdu):
        self.assertEqual(ack_pdu.directive_code_of_acked_pdu, DirectiveType.EOF_PDU)
        self.assertEqual(
            ack_pdu.condition_code_of_acked_pdu,
            ConditionCode.POSITIVE_ACK_LIMIT_REACHED,
        )
        self.assertEqual(ack_pdu.transaction_status, TransactionStatus.ACTIVE)
        self.assertEqual(
            ack_pdu.pdu_file_directive.pdu_header.transaction_seq_num,
            ByteFieldU32.from_bytes(bytes([0x50, 0x00, 0x10, 0x01])),
        )
        self.assertEqual(
            ack_pdu.pdu_file_directive.pdu_header.pdu_conf.source_entity_id,
            ByteFieldU32.from_bytes(bytes([0x10, 0x00, 0x01, 0x02])),
        )
        self.assertEqual(
            ack_pdu.pdu_file_directive.pdu_header.pdu_conf.dest_entity_id,
            ByteFieldU32.from_bytes(bytes([0x30, 0x00, 0x01, 0x03])),
        )
        self.assertEqual(
            ack_pdu.pdu_file_directive.pdu_header.pdu_conf.trans_mode,
            TransmissionMode.UNACKNOWLEDGED,
        )
        self.assertEqual(ack_pdu.packet_len, 19)
