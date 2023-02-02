from unittest import TestCase
from spacepackets import get_lib_logger


class TestMisc(TestCase):
    def test_get_logger(self):
        logger = get_lib_logger()
        self.assertIsNotNone(logger)
