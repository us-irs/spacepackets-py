from unittest import TestCase

from spacepackets.cfdp.conf import (
    set_entity_ids,
    get_entity_ids,
)


class TestConfig(TestCase):
    def test_config(self):
        set_entity_ids(bytes([0x00, 0x01]), bytes([0x02, 0x03]))
        self.assertEqual(get_entity_ids(), (bytes([0x00, 0x01]), bytes([0x02, 0x03])))
