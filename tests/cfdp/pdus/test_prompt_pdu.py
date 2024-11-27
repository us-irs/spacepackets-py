from unittest import TestCase

from spacepackets.cfdp.conf import PduConfig
from spacepackets.cfdp.defs import Direction
from spacepackets.cfdp.pdu import PduFactory, PromptPdu
from spacepackets.cfdp.pdu.prompt import ResponseRequired


class TestPromptPdu(TestCase):
    def setUp(self):
        self.pdu_conf = PduConfig.default()
        self.prompt_pdu = PromptPdu(
            pdu_conf=self.pdu_conf, response_required=ResponseRequired.KEEP_ALIVE
        )

    def test_prompt_pdu(self):
        print(self.prompt_pdu.pack().hex(sep=","))
        prompt_pdu_raw = self.prompt_pdu.pack()
        self.assertEqual(
            prompt_pdu_raw,
            bytes([0x20, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00, 0x09, 0x80]),
        )
        self.assertEqual(self.prompt_pdu.packet_len, 9)
        prompt_pdu_unpacked = PromptPdu.unpack(data=prompt_pdu_raw)
        self.assertEqual(self.prompt_pdu.direction, Direction.TOWARDS_RECEIVER)
        self.assertEqual(self.prompt_pdu.pdu_file_directive.pdu_data_field_len, 2)
        self.assertEqual(self.prompt_pdu.pdu_file_directive.header_len, 8)
        self.assertEqual(prompt_pdu_unpacked.response_required, ResponseRequired.KEEP_ALIVE)
        self.assertEqual(self.prompt_pdu.pdu_file_directive.large_file_flag_set, False)
        prompt_pdu_raw = prompt_pdu_raw[:-1]
        with self.assertRaises(ValueError):
            PromptPdu.unpack(data=prompt_pdu_raw)

    def test_print(self):
        print(self.prompt_pdu)
        self.assertEqual(
            self.prompt_pdu.__repr__(),
            (
                f"PromptPdu(pdu_conf={self.prompt_pdu.pdu_file_directive.pdu_conf!r}, "
                f"response_required={ResponseRequired.KEEP_ALIVE!r})"
            ),
        )

    def test_from_factory(self):
        prompt_raw = self.prompt_pdu.pack()
        pdu_holder = PduFactory.from_raw_to_holder(prompt_raw)
        self.assertIsNotNone(pdu_holder.pdu)
        prompt_pdu = pdu_holder.to_prompt_pdu()
        self.assertIsNotNone(prompt_pdu)
        self.assertEqual(prompt_pdu, self.prompt_pdu)
