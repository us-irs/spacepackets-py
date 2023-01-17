from unittest import TestCase
from spacepackets.ccsds.time import CdsShortTimestamp


class TestTime(TestCase):
    def test_addition(self):
        cds_stamp = CdsShortTimestamp.from_current_time()
