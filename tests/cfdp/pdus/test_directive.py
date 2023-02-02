from unittest import TestCase

from spacepackets.cfdp import LargeFileFlag
from spacepackets.cfdp.conf import PduConfig
from spacepackets.cfdp.pdu import FileDirectivePduBase, DirectiveType


class TestDirective(TestCase):
    def test_file_directive(self):
        pdu_conf = PduConfig.default()
        file_directive_header = FileDirectivePduBase(
            directive_code=DirectiveType.METADATA_PDU,
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
        invalid_fss = bytes([0x00, 0x01])
        with self.assertRaises(ValueError):
            file_directive_header.parse_fss_field(raw_packet=invalid_fss, current_idx=0)
        file_directive_header.pdu_header.file_size = LargeFileFlag.LARGE
        with self.assertRaises(ValueError):
            file_directive_header.parse_fss_field(raw_packet=invalid_fss, current_idx=0)
