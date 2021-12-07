import struct
from unittest import TestCase

from spacepackets.cfdp.definitions import FileSize
from spacepackets.cfdp.pdu.file_directive import FileDirectivePduBase, DirectiveCodes
from spacepackets.util import get_printable_data_string, PrintFormats
from spacepackets.cfdp.pdu.prompt import PromptPdu, ResponseRequired
from spacepackets.cfdp.definitions import LenInBytes, get_transaction_seq_num_as_bytes
from spacepackets.cfdp.pdu import PduHeader, PduType, SegmentMetadataFlag
from spacepackets.cfdp.conf import (
    PduConfig,
    TransmissionModes,
    Direction,
    CrcFlag,
    SegmentationControl,
    set_default_pdu_crc_mode,
    set_default_file_size,
    get_default_file_size,
    get_default_pdu_crc_mode,
    set_entity_ids,
    get_entity_ids,
)


class TestTlvsLvsHeader(TestCase):
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
        self.assertEqual(struct.unpack("!I", len_in_bytes[:])[0], 129302)
        len_in_bytes = get_transaction_seq_num_as_bytes(
            transaction_seq_num=8292392392, byte_length=LenInBytes.EIGHT_BYTES
        )
        self.assertEqual(struct.unpack("!Q", len_in_bytes[:])[0], 8292392392)
        self.assertRaises(
            ValueError, get_transaction_seq_num_as_bytes, 900, LenInBytes.ONE_BYTE
        )
        pdu_conf = PduConfig(
            source_entity_id=bytes([0]),
            dest_entity_id=bytes([0]),
            trans_mode=TransmissionModes.ACKNOWLEDGED,
            direction=Direction.TOWARDS_RECEIVER,
            crc_flag=CrcFlag.NO_CRC,
            seg_ctrl=SegmentationControl.NO_RECORD_BOUNDARIES_PRESERVATION,
            transaction_seq_num=bytes([0]),
        )
        pdu_header = PduHeader(
            pdu_type=PduType.FILE_DIRECTIVE,
            segment_metadata_flag=SegmentMetadataFlag.NOT_PRESENT,
            pdu_data_field_len=0,
            pdu_conf=pdu_conf,
        )
        self.assertEqual(pdu_header.pdu_type, PduType.FILE_DIRECTIVE)
        self.assertEqual(pdu_header.source_entity_id, bytes([0]))
        self.assertEqual(pdu_header.len_entity_id, 1)
        self.assertEqual(pdu_header.trans_mode, TransmissionModes.ACKNOWLEDGED)
        self.assertEqual(pdu_header.direction, Direction.TOWARDS_RECEIVER)
        self.assertEqual(
            pdu_header.segment_metadata_flag, SegmentMetadataFlag.NOT_PRESENT
        )
        self.assertFalse(pdu_header.is_large_file())
        self.assertEqual(pdu_header.transaction_seq_num, bytes([0]))
        self.assertEqual(pdu_header.len_transaction_seq_num, 1)
        self.assertEqual(pdu_header.crc_flag, CrcFlag.NO_CRC)
        pdu_header.crc_flag = CrcFlag.GLOBAL_CONFIG
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
            source_entity_id=bytes([0, 0]), dest_entity_id=bytes([0, 1])
        )
        pdu_header.transaction_seq_num = get_transaction_seq_num_as_bytes(
            300, byte_length=LenInBytes.TWO_BYTES
        )
        pdu_header.trans_mode = TransmissionModes.UNACKNOWLEDGED
        pdu_header.direction = Direction.TOWARDS_SENDER
        pdu_header.crc_flag = CrcFlag.WITH_CRC
        pdu_header.file_size = FileSize.LARGE
        pdu_header.pdu_data_field_len = 300
        pdu_header.seg_ctrl = SegmentationControl.RECORD_BOUNDARIES_PRESERVATION
        pdu_header.segment_metadata_flag = SegmentMetadataFlag.PRESENT

        self.assertTrue(pdu_header.is_large_file())
        pdu_header_packed = pdu_header.pack()
        self.check_fields_case_two(pdu_header_packed=pdu_header_packed)
        set_entity_ids(source_entity_id=bytes(), dest_entity_id=bytes())
        self.assertRaises(ValueError, pdu_header.set_entity_ids, bytes(), bytes())
        self.assertRaises(
            ValueError, pdu_header.set_entity_ids, bytes([0, 1, 2]), bytes()
        )
        self.assertRaises(
            ValueError, pdu_header.set_entity_ids, bytes([0, 1, 2]), bytes([2, 3, 4])
        )
        self.assertRaises(
            ValueError, pdu_header.set_entity_ids, bytes([0, 1, 2, 8]), bytes([2, 3])
        )
        with self.assertRaises(ValueError):
            pdu_header.transaction_seq_num = bytes([0, 1, 2])
        with self.assertRaises(ValueError):
            pdu_header.pdu_data_field_len = 78292
        invalid_pdu_header = bytearray([0, 1, 2])
        self.assertRaises(ValueError, PduHeader.unpack, invalid_pdu_header)
        self.assertRaises(ValueError, PduHeader.unpack, pdu_header_packed[0:6])
        pdu_header_unpacked = PduHeader.unpack(raw_packet=pdu_header_packed)
        self.assertEqual(pdu_header_unpacked.source_entity_id, bytes([0, 0]))
        self.assertEqual(pdu_header_unpacked.dest_entity_id, bytes([0, 1]))
        self.assertEqual(
            pdu_header_unpacked.transaction_seq_num[0] << 8
            | pdu_header_unpacked.transaction_seq_num[1],
            300,
        )

        pdu_conf.source_entity_id = bytes([0])
        pdu_conf.dest_entity_id = bytes([0])
        pdu_conf.transaction_seq_num = bytes([0x00, 0x2C])
        prompt_pdu = PromptPdu(
            reponse_required=ResponseRequired.KEEP_ALIVE, pdu_conf=pdu_conf
        )
        self.assertEqual(prompt_pdu.pdu_file_directive.header_len, 9)
        self.assertEqual(prompt_pdu.packet_len, 10)
        self.assertEqual(prompt_pdu.crc_flag, CrcFlag.WITH_CRC)
        self.assertEqual(prompt_pdu.source_entity_id, bytes([0]))
        self.assertEqual(prompt_pdu.dest_entity_id, bytes([0]))
        self.assertEqual(prompt_pdu.file_size, FileSize.LARGE)
        prompt_pdu.file_size = FileSize.NORMAL
        self.assertEqual(prompt_pdu.file_size, FileSize.NORMAL)
        self.assertEqual(
            prompt_pdu.pdu_file_directive.pdu_header.file_size, FileSize.NORMAL
        )
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

    def test_file_directive(self):
        pdu_conf = PduConfig.empty()
        file_directive_header = FileDirectivePduBase(
            directive_code=DirectiveCodes.METADATA_PDU,
            pdu_conf=pdu_conf,
            directive_param_field_len=0,
        )
        self.assertEqual(file_directive_header.packet_len, 8)
        self.assertEqual(file_directive_header.pdu_data_field_len, 1)
        file_directive_header.pdu_data_field_len = 2
        self.assertEqual(file_directive_header.packet_len, 9)
        file_directive_header_raw = file_directive_header.pack()
        file_directive_header.pdu_data_field_len = 1
        self.assertEqual(len(file_directive_header_raw), 8)
        file_directive_header_raw_invalid = file_directive_header_raw[:-1]
        with self.assertRaises(ValueError):
            FileDirectivePduBase.unpack(raw_packet=file_directive_header_raw_invalid)
        self.assertFalse(file_directive_header._verify_file_len(file_size=pow(2, 33)))
        invalid_fss = bytes([0x00, 0x01])
        with self.assertRaises(ValueError):
            file_directive_header._parse_fss_field(
                raw_packet=invalid_fss, current_idx=0
            )
        file_directive_header.pdu_header.file_size = FileSize.LARGE
        self.assertFalse(file_directive_header._verify_file_len(file_size=pow(2, 65)))
        with self.assertRaises(ValueError):
            file_directive_header._parse_fss_field(
                raw_packet=invalid_fss, current_idx=0
            )

    def test_config(self):
        set_default_pdu_crc_mode(CrcFlag.WITH_CRC)
        self.assertEqual(get_default_pdu_crc_mode(), CrcFlag.WITH_CRC)
        set_default_pdu_crc_mode(CrcFlag.NO_CRC)
        self.assertEqual(get_default_pdu_crc_mode(), CrcFlag.NO_CRC)
        set_default_file_size(FileSize.LARGE)
        self.assertEqual(get_default_file_size(), FileSize.LARGE)
        set_default_file_size(FileSize.NORMAL)
        self.assertEqual(get_default_file_size(), FileSize.NORMAL)
        set_entity_ids(bytes([0x00, 0x01]), bytes([0x02, 0x03]))
        self.assertEqual(get_entity_ids(), (bytes([0x00, 0x01]), bytes([0x02, 0x03])))
