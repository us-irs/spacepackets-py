from unittest import TestCase

from spacepackets.cfdp.conf import PduConfig
from spacepackets.cfdp.pdu import PromptPdu
from spacepackets.cfdp.pdu.prompt import ResponseRequired


class TestPromptPdu(TestCase):
    def test_prompt_pdu(self):
        pdu_conf = PduConfig.default()
        prompt_pdu = PromptPdu(
            pdu_conf=pdu_conf, response_required=ResponseRequired.KEEP_ALIVE
        )
        print(prompt_pdu.pack().hex(sep=","))
        prompt_pdu_raw = prompt_pdu.pack()
        self.assertEqual(
            prompt_pdu_raw,
            bytes([0x20, 0x00, 0x02, 0x11, 0x00, 0x00, 0x00, 0x09, 0x80]),
        )
        self.assertEqual(prompt_pdu.packet_len, 9)
        prompt_pdu_unpacked = PromptPdu.unpack(data=prompt_pdu_raw)
        self.assertEqual(prompt_pdu.pdu_file_directive.pdu_data_field_len, 2)
        self.assertEqual(prompt_pdu.pdu_file_directive.header_len, 8)
        self.assertEqual(
            prompt_pdu_unpacked.response_required, ResponseRequired.KEEP_ALIVE
        )
        self.assertEqual(prompt_pdu.pdu_file_directive.large_file_flag_set, False)
        prompt_pdu_raw = prompt_pdu_raw[:-1]
        with self.assertRaises(ValueError):
            PromptPdu.unpack(data=prompt_pdu_raw)
