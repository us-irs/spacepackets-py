import time
from datetime import timedelta
from unittest import TestCase

from spacepackets.countdown import Countdown


class CountdownTest(TestCase):
    def test_basic(self):
        test_cd = Countdown.from_millis(50)
        self.assertTrue(test_cd.busy())
        self.assertFalse(test_cd.timed_out())
        self.assertTrue(test_cd.remaining_time().total_seconds() * 1000 > 40)
        time.sleep(0.05)
        self.assertTrue(test_cd.timed_out())
        self.assertTrue(test_cd.remaining_time() == timedelta())
        test_cd.timeout = timedelta(seconds=0.1)
        self.assertEqual(test_cd.timeout.total_seconds(), timedelta(seconds=0.1).total_seconds())
        self.assertEqual(test_cd.timeout_ms, 100)
        self.assertTrue(test_cd.busy())
        self.assertFalse(test_cd.timed_out())
        time.sleep(0.1)
        self.assertTrue(test_cd.timed_out())
        test_cd.reset(timedelta(seconds=0.5))
        self.assertTrue(test_cd.remaining_time().total_seconds() * 1000 > 45)
        self.assertTrue(test_cd.busy())
        self.assertFalse(test_cd.timed_out())
        test_cd.reset(timedelta(milliseconds=50))
        self.assertTrue(test_cd.busy())
        test_cd.time_out()
        self.assertTrue(test_cd.timed_out())
