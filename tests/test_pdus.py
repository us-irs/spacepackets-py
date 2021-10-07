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

        print(get_printable_data_string(
            print_format=PrintFormats.BIN, data=ack_pdu_raw, length=len(ack_pdu_raw)
        ))
        print(get_printable_data_string(
            print_format=PrintFormats.HEX, data=ack_pdu_raw
        ))
        self.assertEqual(
            ack_pdu_raw,
            # 0x06 because this is the directive code of ACK PDUs
            # 0x02 because this is the terminated transaction status
            # 0x51 because 0x05 << 4 is the directive code of the Finished PDU and 0b0001 because
            # because this is the value of finished PDUs
            bytes([0x20, 0x00, 0x03, 0x22, 0x00, 0x00, 0x00, 0x01, 0x00, 0x01, 0x06, 0x51, 0x02])
        )
        ack_pdu_unpacked = AckPdu.unpack(raw_packet=ack_pdu_raw)
        self.check_fields_packet_0(ack_pdu=ack_pdu_unpacked)

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
