import struct
from unittest import TestCase

from spacepackets.cfdp.conf import PduConfig, set_entity_ids
from spacepackets.cfdp.defs import (
    LenInBytes,
    TransmissionModes,
    Direction,
    CrcFlag,
    SegmentationControl,
    PduType,
    SegmentMetadataFlag,
    LargeFileFlag,
)
from spacepackets.cfdp.pdu import PduHeader, PromptPdu
from spacepackets.cfdp.pdu.prompt import ResponseRequired
from spacepackets.util import (
    get_printable_data_string,
    PrintFormats,
    ByteFieldU8,
    ByteFieldU32,
    ByteFieldU16,
)


class TestHeader(TestCase):
    # TODO: Split up in smaller test fixtures
    def test_pdu_header(self):
        byte_field = ByteFieldU8(22)
        self.assertEqual(int(byte_field), 22)
        byte_field = ByteFieldU16(5292)
        self.assertEqual(int(byte_field), 5292)
        byte_field = ByteFieldU32(129302)
        self.assertEqual(struct.unpack("!I", byte_field.as_bytes)[0], 129302)
        with self.assertRaises(ValueError):
            ByteFieldU8(900)
        pdu_conf = PduConfig(
            source_entity_id=ByteFieldU8(0),
            dest_entity_id=ByteFieldU8(0),
            trans_mode=TransmissionModes.ACKNOWLEDGED,
            direction=Direction.TOWARDS_RECEIVER,
            crc_flag=CrcFlag.NO_CRC,
            seg_ctrl=SegmentationControl.NO_RECORD_BOUNDARIES_PRESERVATION,
            transaction_seq_num=ByteFieldU8(0),
        )
        pdu_header = PduHeader(
            pdu_type=PduType.FILE_DIRECTIVE,
            segment_metadata_flag=SegmentMetadataFlag.NOT_PRESENT,
            pdu_data_field_len=0,
            pdu_conf=pdu_conf,
        )
        self.assertEqual(pdu_header.pdu_type, PduType.FILE_DIRECTIVE)
        self.assertEqual(pdu_header.source_entity_id, ByteFieldU8(0))
        self.assertEqual(pdu_header.source_entity_id.byte_len, 1)
        self.assertEqual(pdu_header.trans_mode, TransmissionModes.ACKNOWLEDGED)
        self.assertEqual(pdu_header.direction, Direction.TOWARDS_RECEIVER)
        self.assertEqual(
            pdu_header.segment_metadata_flag, SegmentMetadataFlag.NOT_PRESENT
        )
        self.assertFalse(pdu_header.large_file_flag_set)
        self.assertEqual(pdu_header.transaction_seq_num, ByteFieldU8(0))
        self.assertEqual(pdu_header.transaction_seq_num.byte_len, 1)
        self.assertEqual(pdu_header.crc_flag, CrcFlag.NO_CRC)
        self.assertEqual(
            pdu_header.seg_ctrl, SegmentationControl.NO_RECORD_BOUNDARIES_PRESERVATION
        )
        self.assertEqual(pdu_header.header_len, 7)
        pdu_header_packed = pdu_header.pack()
        string = get_printable_data_string(
            print_format=PrintFormats.HEX, data=pdu_header_packed
        )
        self.assertEqual(string, "hex [20,00,00,11,00,00,00]")
        self.check_fields_case_one(pdu_header_packed=pdu_header_packed)
        pdu_header_unpacked = PduHeader.unpack(raw_packet=pdu_header_packed)
        pdu_header_repacked = pdu_header_unpacked.pack()
        self.check_fields_case_one(pdu_header_packed=pdu_header_repacked)

        pdu_header.pdu_type = PduType.FILE_DATA
        pdu_header.set_entity_ids(
            source_entity_id=ByteFieldU16(0), dest_entity_id=ByteFieldU16(1)
        )
        pdu_header.transaction_seq_num = ByteFieldU16(300)
        pdu_header.trans_mode = TransmissionModes.UNACKNOWLEDGED
        pdu_header.direction = Direction.TOWARDS_SENDER
        pdu_header.crc_flag = CrcFlag.WITH_CRC
        pdu_header.file_flag = LargeFileFlag.LARGE
        pdu_header.pdu_data_field_len = 300
        pdu_header.seg_ctrl = SegmentationControl.RECORD_BOUNDARIES_PRESERVATION
        pdu_header.segment_metadata_flag = SegmentMetadataFlag.PRESENT

        self.assertTrue(pdu_header.large_file_flag_set)
        pdu_header_packed = pdu_header.pack()
        self.check_fields_case_two(pdu_header_packed=pdu_header_packed)
        set_entity_ids(source_entity_id=bytes(), dest_entity_id=bytes())
        with self.assertRaises(ValueError):
            pdu_header.pdu_data_field_len = 78292
        invalid_pdu_header = bytearray([0, 1, 2])
        self.assertRaises(ValueError, PduHeader.unpack, invalid_pdu_header)
        self.assertRaises(ValueError, PduHeader.unpack, pdu_header_packed[0:6])
        pdu_header_unpacked = PduHeader.unpack(raw_packet=pdu_header_packed)
        self.assertEqual(pdu_header_unpacked.source_entity_id, ByteFieldU16(0))
        self.assertEqual(pdu_header_unpacked.dest_entity_id, ByteFieldU16(1))
        self.assertEqual(
            int(pdu_header_unpacked.transaction_seq_num),
            300,
        )

        pdu_conf.source_entity_id = ByteFieldU8(0)
        pdu_conf.dest_entity_id = ByteFieldU8(0)
        pdu_conf.transaction_seq_num = ByteFieldU16.from_bytes(bytes([0x00, 0x2C]))
        prompt_pdu = PromptPdu(
            response_required=ResponseRequired.KEEP_ALIVE, pdu_conf=pdu_conf
        )
        self.assertEqual(prompt_pdu.pdu_file_directive.header_len, 9)
        self.assertEqual(prompt_pdu.packet_len, 10)
        self.assertEqual(prompt_pdu.crc_flag, CrcFlag.WITH_CRC)
        self.assertEqual(prompt_pdu.source_entity_id, ByteFieldU8(0))
        self.assertEqual(prompt_pdu.dest_entity_id, ByteFieldU8(0))
        self.assertEqual(prompt_pdu.file_flag, LargeFileFlag.LARGE)
        prompt_pdu.file_flag = LargeFileFlag.NORMAL
        self.assertEqual(prompt_pdu.file_flag, LargeFileFlag.NORMAL)
        self.assertEqual(prompt_pdu.pdu_file_directive.file_flag, LargeFileFlag.NORMAL)
        prompt_pdu.crc_flag = CrcFlag.NO_CRC
        self.assertEqual(prompt_pdu.crc_flag, CrcFlag.NO_CRC)
        self.assertEqual(
            prompt_pdu.pdu_file_directive.pdu_header.crc_flag, CrcFlag.NO_CRC
        )

    def check_fields_case_one(self, pdu_header_packed: bytes):
        self.assertEqual(len(pdu_header_packed), 7)
        # Check version field
        self.assertEqual((pdu_header_packed[0] & 0xE0) >> 5, 0b001)
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
        self.assertEqual((pdu_header_packed[0] & 0xE0) >> 5, 0b001)
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