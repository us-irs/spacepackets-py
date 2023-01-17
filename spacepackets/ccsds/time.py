from __future__ import annotations
import datetime
import math
import enum
import struct
import time
from abc import abstractmethod, ABC
from typing import Optional

import deprecation
from spacepackets import __version__

DAYS_CCSDS_TO_UNIX = -4383
SECONDS_PER_DAY = 86400
MS_PER_DAY = SECONDS_PER_DAY * 1000
UNIX_EPOCH = datetime.datetime.utcfromtimestamp(0)


class CcsdsTimeCodeId(enum.IntEnum):
    NONE = 0
    CUC_CCSDS_EPOCH = 0b001
    CUC_AGENCY_EPOCH = 0b010
    CDS = 0b100
    CCS = 0b101


def convert_unix_days_to_ccsds_days(unix_days: int) -> int:
    """Convert Unix days to CCSDS days

    CCSDS epoch: 1958 Januar 1
    Unix epoch: 1970 January 1
    """
    return unix_days - DAYS_CCSDS_TO_UNIX


def convert_ccsds_days_to_unix_days(ccsds_days: int) -> int:
    """Convert CCSDS days to Unix days

    CCSDS epoch: 1958 Januar 1
    Unix epoch: 1970 January 1
    """
    return ccsds_days + DAYS_CCSDS_TO_UNIX


def read_p_field(p_field: int) -> CcsdsTimeCodeId:
    """Read the p field and return the CCSDS Time Code ID
    :param p_field:
    :return:
    :raise IndexError: P field has invalid value
    """
    return CcsdsTimeCodeId((p_field & 0x70) >> 4)


class CcsdsTimeProvider(ABC):
    @property
    @abstractmethod
    def pfield(self) -> bytes:
        pass

    @property
    @abstractmethod
    def len(self) -> int:
        pass

    @abstractmethod
    def pack(self) -> bytearray:
        pass

    @abstractmethod
    def read_from_raw(self, timestamp: bytes):
        pass

    @abstractmethod
    def as_unix_seconds(self) -> float:
        pass

    @deprecation.deprecated(
        deprecated_in="0.14.0rc0",
        current_version=__version__,
        details="use as_date_time instead",
    )
    def as_datetime(self) -> datetime:
        self.as_date_time()

    @abstractmethod
    def as_date_time(self) -> datetime:
        pass

    def as_time_string(self) -> str:
        return self.as_date_time().strftime("%Y-%m-%d %H:%M:%S.%f")

    def ccsds_time_code(self) -> int:
        if self.pfield == bytes():
            return 0
        return (self.pfield[0] >> 4) & 0b111


class CdsShortTimestamp(CcsdsTimeProvider):
    """Unpacks the time datafield of the TM packet. Right now, CDS Short timeformat is used,
    and the size of the time stamp is expected to be seven bytes.
    """

    CDS_SHORT_ID = 0b100
    TIMESTAMP_SIZE = 7

    def __init__(
        self, ccsds_days: int, ms_of_day: int, init_dt_unix_stamp: bool = True
    ):
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
            self._date_time = datetime.datetime(1970, 1, 1) + datetime.timedelta(
                seconds=self._unix_seconds
            )
        else:
            self._date_time = datetime.datetime.utcfromtimestamp(self._unix_seconds)

    @property
    def pfield(self) -> bytes:
        return self.__p_field

    @property
    def len(self) -> int:
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
    def unpack(cls, raw_stamp: bytes) -> CdsShortTimestamp:
        ccsds_days, ms_of_day = CdsShortTimestamp.unpack_from_raw(raw_stamp)
        return cls(ccsds_days=ccsds_days, ms_of_day=ms_of_day)

    def read_from_raw(self, raw_stamp: bytes):
        (self._unix_seconds, self._ms_of_day) = CdsShortTimestamp.unpack_from_raw(
            raw_stamp
        )
        self._setup()

    @staticmethod
    def unpack_from_raw(raw: bytes) -> (int, int):
        p_field = raw[0]
        if (p_field >> 4) & 0b111 != CcsdsTimeCodeId.CDS:
            raise ValueError(
                f"Invalid CCSDS Time Code {p_field}, expected {CcsdsTimeCodeId.CDS}"
            )
        ccsds_days = struct.unpack("!H", raw[1:3])[0]
        ms_of_day = struct.unpack("!I", raw[3:7])[0]
        return ccsds_days, ms_of_day

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(ccsds_days={self._ccsds_days!r}, "
            f"ms_of_day={self._ms_of_day!r})"
        )

    def __str__(self):
        return f"Date {self._date_time!r} with representation {self!r}"

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
        self._ms_of_day += timedelta.microseconds / 1000 + timedelta.seconds * 1000
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
    def from_current_time(cls) -> CdsShortTimestamp:
        """Returns a seven byte CDS short timestamp with the current time"""
        return cls.from_unix_days(
            unix_days=(datetime.datetime.utcnow() - UNIX_EPOCH).days,
            ms_of_day=cls.ms_of_today(),
        )

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
