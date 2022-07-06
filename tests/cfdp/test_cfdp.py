from unittest import TestCase

from spacepackets.cfdp.conf import (
    CrcFlag,
    set_default_pdu_crc_mode,
    get_default_pdu_crc_mode,
    set_entity_ids,
    get_entity_ids,
)


class TestConfig(TestCase):
    def test_config(self):
        set_default_pdu_crc_mode(CrcFlag.WITH_CRC)
        self.assertEqual(get_default_pdu_crc_mode(), CrcFlag.WITH_CRC)
        set_default_pdu_crc_mode(CrcFlag.NO_CRC)
        self.assertEqual(get_default_pdu_crc_mode(), CrcFlag.NO_CRC)
        set_entity_ids(bytes([0x00, 0x01]), bytes([0x02, 0x03]))
        self.assertEqual(get_entity_ids(), (bytes([0x00, 0x01]), bytes([0x02, 0x03])))
