import struct
from unittest import TestCase

from spacepackets.cfdp.definitions import FileSize
from spacepackets.cfdp.tlv import CfdpTlv, TlvTypes
from spacepackets.cfdp.lv import CfdpLv
from spacepackets.cfdp.definitions import LenInBytes, get_transaction_seq_num_as_bytes
from spacepackets.cfdp.pdu import PduHeader, PduType, TransmissionModes, Direction, \
    SegmentMetadataFlag, CrcFlag, SegmentationControl


class TestCfdp(TestCase):

    def test_tlvs(self):
        test_tlv = CfdpTlv(
            tlv_type=TlvTypes.FILESTORE_REQUEST,
            value=bytes([0, 1, 2, 3, 4])
        )
        self.assertEqual(test_tlv.tlv_type, TlvTypes.FILESTORE_REQUEST)
        self.assertEqual(test_tlv.length, 5)
        self.assertEqual(test_tlv.value, bytes([0, 1, 2, 3, 4]))
        self.assertEqual(test_tlv.get_total_length(), 7)

        test_tlv_package = test_tlv.pack()
        test_tlv_unpacked = CfdpTlv.unpack(raw_bytes=test_tlv_package)
        self.assertEqual(test_tlv_unpacked.tlv_type, TlvTypes.FILESTORE_REQUEST)
        self.assertEqual(test_tlv_unpacked.length, 5)
        self.assertEqual(test_tlv_unpacked.value, bytes([0, 1, 2, 3, 4]))

        # Length field missmatch
        another_tlv = bytes([TlvTypes.ENTITY_ID, 1, 3, 4])
        another_tlv_unpacked = CfdpTlv.unpack(raw_bytes=another_tlv)
        self.assertEqual(another_tlv_unpacked.value, bytes([3]))
        self.assertEqual(another_tlv_unpacked.length, 1)

        faulty_tlv = bytes([TlvTypes.FILESTORE_REQUEST, 200, 2, 3])
        self.assertRaises(ValueError, CfdpTlv.unpack, faulty_tlv)
        # Too much too pack
        faulty_values = bytes(300)
        self.assertRaises(ValueError, CfdpTlv, TlvTypes.FILESTORE_REQUEST, faulty_values)
        # Too short to unpack
        faulty_tlv = bytes([0])
        self.assertRaises(ValueError, CfdpTlv.unpack, faulty_tlv)
        # Invalid type when unpacking
        faulty_tlv = bytes([TlvTypes.ENTITY_ID + 3, 2, 1, 2])
        self.assertRaises(ValueError, CfdpTlv.unpack, faulty_tlv)

    def test_lvs(self):
        test_values = bytes([0, 1, 2])
        test_lv = CfdpLv(
            value=test_values
        )
        self.assertEqual(test_lv.value, test_values)
        self.assertEqual(test_lv.len, 3)
        self.assertEqual(test_lv.get_total_len(), 4)
        test_lv_packed = test_lv.pack()
        self.assertEqual(len(test_lv_packed), 4)
        self.assertEqual(test_lv_packed[0], 3)
        self.assertEqual(test_lv_packed[1: 1 + 3], test_values)

        CfdpLv.unpack(raw_bytes=test_lv_packed)
        self.assertEqual(test_lv.value, test_values)
        self.assertEqual(test_lv.len, 3)
        self.assertEqual(test_lv.get_total_len(), 4)

        # Too much too pack
        faulty_values = bytearray(300)
        self.assertRaises(ValueError, CfdpLv, faulty_values)
        # Too large to unpack
        faulty_values[0] = 20
        self.assertRaises(ValueError, CfdpLv.unpack, faulty_values[0:15])
        # Too short to unpack
        faulty_lv = bytes([0])
        self.assertRaises(ValueError, CfdpTlv.unpack, faulty_lv)

    def test_pdu_header(self):
        len_in_bytes = get_transaction_seq_num_as_bytes(
            transaction_seq_num=22, byte_length=LenInBytes.ONE_BYTE
        )
        self.assertEqual(len_in_bytes[0], 22)
        len_in_bytes = get_transaction_seq_num_as_bytes(
            transaction_seq_num=5292, byte_length=LenInBytes.TWO_BYTES
        )
        self.assertEqual(len_in_bytes[0] << 8 | len_in_bytes[1], 5292)
        len_in_bytes = get_transaction_seq_num_as_bytes(
            transaction_seq_num=129302, byte_length=LenInBytes.FOUR_BYTES
        )
        self.assertEqual(struct.unpack('!I', len_in_bytes[:])[0], 129302)
        len_in_bytes = get_transaction_seq_num_as_bytes(
            transaction_seq_num=8292392392, byte_length=LenInBytes.EIGHT_BYTES
        )
        self.assertEqual(struct.unpack('!Q', len_in_bytes[:])[0], 8292392392)
        self.assertRaises(
            ValueError, get_transaction_seq_num_as_bytes, 900, LenInBytes.ONE_BYTE
        )
        pdu_header = PduHeader(
            pdu_type=PduType.FILE_DIRECTIVE,
            source_entity_id=bytes([0]),
            dest_entity_id=bytes([0]),
            trans_mode=TransmissionModes.ACKNOWLEDGED,
            direction=Direction.TOWARDS_RECEIVER,
            segment_metadata_flag=SegmentMetadataFlag.NOT_PRESENT,
            transaction_seq_num=bytes([0]),
            crc_flag=CrcFlag.NO_CRC,
            seg_ctrl=SegmentationControl.NO_RECORD_BOUNDARIES_PRESERVATION
        )
        self.assertEqual(pdu_header.pdu_type, PduType.FILE_DIRECTIVE)
        self.assertEqual(pdu_header.source_entity_id, bytes([0]))
        self.assertEqual(pdu_header.len_entity_id, 1)
        self.assertEqual(pdu_header.trans_mode, TransmissionModes.ACKNOWLEDGED)
        self.assertEqual(pdu_header.direction, Direction.TOWARDS_RECEIVER)
        self.assertEqual(pdu_header.segment_metadata_flag, SegmentMetadataFlag.NOT_PRESENT)
        self.assertEqual(pdu_header.transaction_seq_num, bytes([0]))
        self.assertEqual(pdu_header.len_transaction_seq_num, 1)
        self.assertEqual(pdu_header.crc_flag, CrcFlag.NO_CRC)
        self.assertEqual(
            pdu_header.segmentation_control, SegmentationControl.NO_RECORD_BOUNDARIES_PRESERVATION
        )
        self.assertEqual(pdu_header.get_packet_len(), 7)
        pdu_header_packed = pdu_header.pack()
        self.check_fields_case_one(pdu_header_packed=pdu_header_packed)
        pdu_header_unpacked = PduHeader.unpack(raw_packet=pdu_header_packed)
        pdu_header_repacked = pdu_header_unpacked.pack()
        self.check_fields_case_one(pdu_header_packed=pdu_header_repacked)

        pdu_header.pdu_type = PduType.FILE_DATA
        pdu_header.set_entity_ids(source_entity_id=bytes([0, 0]), dest_entity_id=bytes([0, 1]))
        pdu_header.set_transaction_seq_num(
            get_transaction_seq_num_as_bytes(300, byte_length=LenInBytes.TWO_BYTES)
        )
        pdu_header.trans_mode = TransmissionModes.UNACKNOWLEDGED
        pdu_header.direction = Direction.TOWARDS_SENDER
        pdu_header.set_crc_flag(crc_flag=CrcFlag.WITH_CRC)
        pdu_header.set_file_size(file_size=FileSize.LARGE)
        pdu_header.set_pdu_data_field_length(new_length=300)
        pdu_header.segmentation_control = SegmentationControl.RECORD_BOUNDARIES_PRESERVATION
        pdu_header.segment_metadata_flag = SegmentMetadataFlag.PRESENT

        pdu_header_packed = pdu_header.pack()
        self.check_fields_case_two(pdu_header_packed=pdu_header_packed)

        self.assertRaises(ValueError, pdu_header.set_entity_ids, bytes(), bytes())
        self.assertRaises(ValueError, pdu_header.set_entity_ids, bytes([0, 1, 2]), bytes())
        self.assertRaises(
            ValueError, pdu_header.set_entity_ids, bytes([0, 1, 2]), bytes([2, 3, 4])
        )
        self.assertRaises(
            ValueError, pdu_header.set_entity_ids, bytes([0, 1, 2, 8]), bytes([2, 3])
        )
        self.assertRaises(
            ValueError, pdu_header.set_transaction_seq_num, bytes([0, 1, 2])
        )
        self.assertRaises(
            ValueError, pdu_header.set_pdu_data_field_length, 78292
        )
        invalid_pdu_header = bytearray([0, 1, 2])
        self.assertRaises(ValueError, PduHeader.unpack, invalid_pdu_header)
        self.assertRaises(ValueError, PduHeader.unpack, pdu_header_packed[0:6])
        pdu_header_unpacked = PduHeader.unpack(raw_packet=pdu_header_packed)
        self.assertEqual(pdu_header_unpacked.source_entity_id, bytes([0, 0]))
        self.assertEqual(pdu_header_unpacked.dest_entity_id, bytes([0, 1]))
        self.assertEqual(
            pdu_header_unpacked.transaction_seq_num[0] << 8 |
            pdu_header_unpacked.transaction_seq_num[1], 300
        )

    def check_fields_case_one(self, pdu_header_packed: bytes):
        self.assertEqual(len(pdu_header_packed), 7)
        # Check version field
        self.assertEqual((pdu_header_packed[0] & 0xe0) >> 5, 0b001)
        # PDU type
        self.assertEqual((pdu_header_packed[0] & 0x10) >> 4, 0)
        # Direction
        self.assertEqual((pdu_header_packed[0] & 0x08) >> 3, 0)
        # Transmission Mode
        self.assertEqual((pdu_header_packed[0] & 0x04) >> 2, 0)
        # CRC flag
        self.assertEqual((pdu_header_packed[0] & 0x02) >> 1, 0)
        # Large file flag
        self.assertEqual(pdu_header_packed[0] & 0x01, 0)
        # Data field length
        self.assertEqual(pdu_header_packed[1] << 8 | pdu_header_packed[2], 0)
        # Segmentation Control
        self.assertEqual((pdu_header_packed[3] & 0x80) >> 7, 0)
        # Length of entity IDs
        self.assertEqual((pdu_header_packed[3] & 0x70) >> 4, LenInBytes.ONE_BYTE)
        # Segment metadata flag
        self.assertEqual((pdu_header_packed[3] & 0x08) >> 3, 0)
        # Length of transaction sequence number
        self.assertEqual(pdu_header_packed[3] & 0b111, LenInBytes.ONE_BYTE)
        # Source entity ID
        self.assertEqual(pdu_header_packed[4], 0)
        # Transaction Sequence number
        self.assertEqual(pdu_header_packed[5], 0)
        # Destination ID
        self.assertEqual(pdu_header_packed[6], 0)

    def check_fields_case_two(self, pdu_header_packed: bytes):
        self.assertEqual(len(pdu_header_packed), 10)
        # Check version field
        self.assertEqual((pdu_header_packed[0] & 0xe0) >> 5, 0b001)
        # PDU type
        self.assertEqual(pdu_header_packed[0] & 0x10 >> 4, 1)
        # Direction
        self.assertEqual(pdu_header_packed[0] & 0x08 >> 3, 1)
        # Transmission Mode
        self.assertEqual(pdu_header_packed[0] & 0x04 >> 2, 1)
        # CRC flag
        self.assertEqual(pdu_header_packed[0] & 0x02 >> 1, 1)
        # Large file flag
        self.assertEqual(pdu_header_packed[0] & 0x01, 1)
        # Data field length
        self.assertEqual(pdu_header_packed[1] << 8 | pdu_header_packed[2], 300)
        # Segmentation Control
        self.assertEqual((pdu_header_packed[3] & 0x80) >> 7, 1)
        # Length of entity IDs
        self.assertEqual((pdu_header_packed[3] & 0x70) >> 4, LenInBytes.TWO_BYTES)
        # Segment metadata flag
        self.assertEqual((pdu_header_packed[3] & 0x08) >> 3, 1)
        # Length of transaction sequence number
        self.assertEqual(pdu_header_packed[3] & 0b111, LenInBytes.TWO_BYTES)
        # Source entity ID
        self.assertEqual(pdu_header_packed[4:6], bytes([0, 0]))
        # Transaction Sequence number
        self.assertEqual(pdu_header_packed[6] << 8 | pdu_header_packed[7], 300)
        # Destination ID
        self.assertEqual(pdu_header_packed[8:10], bytes([0, 1]))
