import datetime
import struct
from unittest import TestCase
from spacepackets.ccsds.time import (
    CdsShortTimestamp,
    SECONDS_PER_DAY,
    MS_PER_DAY,
)
from spacepackets.ccsds.time.common import (
    convert_ccsds_days_to_unix_days,
    convert_unix_days_to_ccsds_days,
)


class TestTime(TestCase):
    def test_basic(self):
        empty_stamp = CdsShortTimestamp(0, 0)
        self.assertEqual(
            empty_stamp.pfield, bytes([CdsShortTimestamp.CDS_SHORT_ID << 4])
        )
        self.assertEqual(empty_stamp.ccsds_days, 0)
        self.assertEqual(empty_stamp.ms_of_day, 0)
        dt = empty_stamp.as_date_time()
        self.assertEqual(dt.year, 1958)
        self.assertEqual(dt.month, 1)
        self.assertEqual(dt.day, 1)
        self.assertEqual(dt.hour, 0)
        self.assertEqual(dt.minute, 0)
        self.assertEqual(dt.second, 0)
        unix_seconds = empty_stamp.as_unix_seconds()
        self.assertEqual(
            unix_seconds, convert_ccsds_days_to_unix_days(0) * SECONDS_PER_DAY
        )

    def test_basic_from_dt(self):
        cds_stamp = CdsShortTimestamp.from_date_time(
            datetime.datetime(
                year=1970,
                month=1,
                day=1,
                hour=0,
                minute=0,
                second=0,
                tzinfo=datetime.timezone.utc,
            )
        )
        expected_days = convert_unix_days_to_ccsds_days(0)
        self.assertEqual(cds_stamp.ccsds_days, expected_days)
        self.assertEqual(cds_stamp.ms_of_day, 0)
        unix_seconds = cds_stamp.as_unix_seconds()
        self.assertTrue(abs(unix_seconds - round(unix_seconds)) < 0.0001)

    def test_addition_0(self):
        empty_stamp = CdsShortTimestamp(0, 0)
        empty_stamp += datetime.timedelta(seconds=10)
        self.assertEqual(empty_stamp.ms_of_day, 10000)
        self.assertEqual(empty_stamp.ccsds_days, 0)

    def test_addition_1(self):
        empty_stamp = CdsShortTimestamp(0, 0)
        empty_stamp += datetime.timedelta(days=2, minutes=12, milliseconds=15)
        self.assertEqual(empty_stamp.ms_of_day, 12 * 60 * 1000 + 15)
        self.assertEqual(empty_stamp.ccsds_days, 2)
        stamp_packed = empty_stamp.pack()
        self.assertEqual(struct.unpack("!H", stamp_packed[1:3])[0], 2)
        self.assertEqual(struct.unpack("!I", stamp_packed[3:7])[0], 12 * 60 * 1000 + 15)

    def test_invalid_addition(self):
        with self.assertRaises(TypeError):
            CdsShortTimestamp(0, 0) + CdsShortTimestamp(0, 0)

    def test_addition_days_increment(self):
        stamp = CdsShortTimestamp(0, MS_PER_DAY - 5)
        stamp += datetime.timedelta(milliseconds=10)
        self.assertEqual(stamp.ccsds_days, 1)
        self.assertEqual(stamp.ms_of_day, 5)

    def test_dt_is_utc(self):
        empty_stamp = CdsShortTimestamp(0, 0)
        dt = empty_stamp.as_date_time()
        self.assertEqual(dt.tzinfo, datetime.timezone.utc)
        self.assertEqual(dt.tzinfo.utcoffset(dt), datetime.timedelta(0))

    def test_compare_from_now_against_manually_created(self):
        stamp = CdsShortTimestamp.from_now()
        ccsds_days = stamp.ccsds_days
        ms_of_day = stamp.ms_of_day
        new_stamp = CdsShortTimestamp(ccsds_days, ms_of_day)
        self.assertEqual(new_stamp, stamp)
        self.assertEqual(new_stamp.as_unix_seconds(), new_stamp.as_unix_seconds())

    def test_read_from_raw(self):
        stamp = CdsShortTimestamp(30000, 1000)
        stamp_raw = stamp.pack()
        empty_stamp = CdsShortTimestamp.empty()
        empty_stamp.read_from_raw(stamp_raw)
        self.assertEqual(empty_stamp, stamp)
