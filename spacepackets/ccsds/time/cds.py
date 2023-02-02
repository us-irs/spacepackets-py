from __future__ import annotations
import datetime
import enum
import math
import struct
import time
from typing import Optional

import deprecation

from spacepackets import __version__
from spacepackets.exceptions import BytesTooShortError
from spacepackets.ccsds.time.common import (
    CcsdsTimeProvider,
    convert_ccsds_days_to_unix_days,
    SECONDS_PER_DAY,
    convert_unix_days_to_ccsds_days,
    CcsdsTimeCodeId,
    MS_PER_DAY,
)


class LenOfDaysSegment(enum.IntEnum):
    DAYS_16_BITS = 0
    DAYS_24_BITS = 1


def len_of_day_seg_from_pfield(pfield: int) -> LenOfDaysSegment:
    """Extract length of day segment from the pfield"""
    return LenOfDaysSegment((pfield >> 2) & 0b1)


class CdsShortTimestamp(CcsdsTimeProvider):
    """Unpacks the time datafield of the TM packet. Right now, CDS Short timeformat is used,
    and the size of the time stamp is expected to be seven bytes.

    >>> from spacepackets.ccsds.time import CcsdsTimeCodeId
    >>> cds_short_now = CdsShortTimestamp.from_now()
    >>> cds_short_now.len_packed
    7
    >>> hex(cds_short_now.pfield[0])
    '0x40'
    """

    CDS_SHORT_ID = 0b100
    TIMESTAMP_SIZE = 7

    def __init__(
        self, ccsds_days: int, ms_of_day: int, init_dt_unix_stamp: bool = True
    ):
        """Create a stamp from the contained values directly.

        >>> zero_stamp = CdsShortTimestamp(ccsds_days=0, ms_of_day=0)
        >>> zero_stamp.ccsds_days
        0
        >>> zero_stamp.ms_of_day
        0
        >>> unix_zero_as_ccsds = CdsShortTimestamp(ccsds_days=convert_ccsds_days_to_unix_days(0), ms_of_day=0) # noqa: E501
        >>> unix_zero_as_ccsds.ccsds_days
        -4383
        >>> CdsShortTimestamp(0x0102, 0x03040506).pack().hex(sep=',')
        '40,01,02,03,04,05,06'
        """
        self.__p_field = bytes([CdsShortTimestamp.CDS_SHORT_ID << 4])
        # CCSDS recommends a 1958 Januar 1 epoch, which is different from the Unix epoch
        self._ccsds_days = ccsds_days
        self._unix_seconds = 0
        self._ms_of_day = ms_of_day
        if init_dt_unix_stamp:
            self._setup()

    def _setup(self):
        self._calculate_unix_seconds()
        self._calculate_date_time()

    def _calculate_unix_seconds(self):
        unix_days = convert_ccsds_days_to_unix_days(self._ccsds_days)
        self._unix_seconds = unix_days * SECONDS_PER_DAY
        seconds_of_day = self._ms_of_day / 1000.0
        if self._unix_seconds < 0:
            self._unix_seconds -= seconds_of_day
        else:
            self._unix_seconds += seconds_of_day

    def _calculate_date_time(self):
        if self._unix_seconds < 0:
            self._date_time = datetime.datetime(
                1970, 1, 1, tzinfo=datetime.timezone.utc
            ) + datetime.timedelta(seconds=self._unix_seconds)
        else:
            self._date_time = datetime.datetime.fromtimestamp(
                self._unix_seconds, tz=datetime.timezone.utc
            )

    @property
    def pfield(self) -> bytes:
        return self.__p_field

    @property
    def len_packed(self) -> int:
        return CdsShortTimestamp.TIMESTAMP_SIZE

    @property
    def ccsds_days(self) -> int:
        return self._ccsds_days

    @property
    def ms_of_day(self) -> int:
        return self._ms_of_day

    def pack(self) -> bytearray:
        cds_packet = bytearray()
        cds_packet.extend(self.__p_field)
        cds_packet.extend(struct.pack("!H", self._ccsds_days))
        cds_packet.extend(struct.pack("!I", self._ms_of_day))
        return cds_packet

    @classmethod
    def from_unix_days(cls, unix_days: int, ms_of_day: int) -> CdsShortTimestamp:
        return cls(
            ccsds_days=convert_unix_days_to_ccsds_days(unix_days=unix_days),
            ms_of_day=ms_of_day,
        )

    @classmethod
    def empty(cls, init_dt_unix_stamp: bool = True):
        """Empty instance containing only zero for all fields.

        :return:
        """
        return cls(ccsds_days=0, ms_of_day=0, init_dt_unix_stamp=init_dt_unix_stamp)

    @classmethod
    def unpack(cls, data: bytes) -> CdsShortTimestamp:
        ccsds_days, ms_of_day = CdsShortTimestamp.unpack_from_raw(data)
        return cls(ccsds_days=ccsds_days, ms_of_day=ms_of_day)

    def read_from_raw(self, data: bytes):
        """Updates the instance from a given raw CDS short timestamp

        :param data:
        :return:
        """
        (self._ccsds_days, self._ms_of_day) = CdsShortTimestamp.unpack_from_raw(data)
        self._setup()

    @staticmethod
    def unpack_from_raw(data: bytes) -> (int, int):
        if len(data) < CdsShortTimestamp.TIMESTAMP_SIZE:
            raise BytesTooShortError(CdsShortTimestamp.TIMESTAMP_SIZE, len(data))
        p_field = data[0]
        if (p_field >> 4) & 0b111 != CcsdsTimeCodeId.CDS:
            raise ValueError(
                f"invalid CCSDS Time Code {p_field}, expected {CcsdsTimeCodeId.CDS}"
            )
        len_of_day = len_of_day_seg_from_pfield(p_field)
        if len_of_day != LenOfDaysSegment.DAYS_16_BITS:
            raise ValueError(
                f"invalid length of days field {len_of_day} for CDS short timestamp"
            )
        ccsds_days = struct.unpack("!H", data[1:3])[0]
        ms_of_day = struct.unpack("!I", data[3:7])[0]
        return ccsds_days, ms_of_day

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(ccsds_days={self._ccsds_days!r}, "
            f"ms_of_day={self._ms_of_day!r})"
        )

    def __str__(self):
        return f"Date {self._date_time!r} with representation {self!r}"

    def __eq__(self, other: CdsShortTimestamp):
        return (self.ccsds_days == other.ccsds_days) and (
            self.ms_of_day == other.ms_of_day
        )

    def __add__(self, timedelta: datetime.timedelta):
        """Allows adding timedelta to the CDS timestamp provider.

        :param timedelta:
        :raises TypeError: Type other than timedelta was passed.
        :raises OverflowError: CCSDS days would have an invalid value (exceeding value representable
            by 16 bits) after increment.
        :return:
        """
        if not isinstance(timedelta, datetime.timedelta):
            raise TypeError("can only handle timedelta for additions")
        self._ms_of_day += timedelta.microseconds // 1000 + timedelta.seconds * 1000
        if self._ms_of_day > MS_PER_DAY:
            self._ms_of_day -= MS_PER_DAY
            self._ccsds_days += 1
            if self._ccsds_days > pow(2, 16) - 1:
                raise OverflowError("CCSDS days overflow")
        self._ccsds_days += timedelta.days
        if self._ccsds_days > pow(2, 16) - 1:
            raise OverflowError("CCSDS days overflow")
        self._setup()
        return self

    @classmethod
    def from_now(cls) -> CdsShortTimestamp:
        """Returns a seven byte CDS short timestamp with the current time."""
        return cls.from_date_time(datetime.datetime.now(tz=datetime.timezone.utc))

    @classmethod
    @deprecation.deprecated(
        deprecated_in="0.14.0rc1",
        current_version=__version__,
        details="use from_now instead",
    )
    def from_current_time(cls) -> CdsShortTimestamp:
        return cls.from_now()

    @classmethod
    def from_date_time(cls, dt: datetime.datetime) -> CdsShortTimestamp:
        instance = cls.empty(False)
        instance._date_time = dt
        instance._unix_seconds = dt.timestamp()
        full_unix_secs = int(math.floor(instance._unix_seconds))
        subsec_millis = int((instance._unix_seconds - full_unix_secs) * 1000)
        unix_days = int(full_unix_secs / SECONDS_PER_DAY)
        secs_of_day = full_unix_secs % SECONDS_PER_DAY
        instance._ms_of_day = secs_of_day * 1000 + subsec_millis
        instance._ccsds_days = convert_unix_days_to_ccsds_days(unix_days)
        return instance

    @staticmethod
    def ms_of_today(seconds_since_epoch: Optional[float] = None):
        if seconds_since_epoch is None:
            seconds_since_epoch = time.time()
        fraction_ms = seconds_since_epoch - math.floor(seconds_since_epoch)
        return int(
            math.floor((seconds_since_epoch % SECONDS_PER_DAY) * 1000 + fraction_ms)
        )

    def as_unix_seconds(self) -> float:
        return self._unix_seconds

    def as_date_time(self) -> datetime.datetime:
        return self._date_time
