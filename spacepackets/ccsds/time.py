from __future__ import annotations
import datetime
import math
import enum
import struct
import time
from abc import abstractmethod, ABC
from typing import Optional

DAYS_CCSDS_TO_UNIX = -4383
SECONDS_PER_DAY = 86400
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


class CcsdsTimeCode(ABC):
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
    def as_unix_seconds(self) -> int:
        pass

    @abstractmethod
    def as_time_string(self) -> str:
        pass

    def ccsds_time_code(self) -> int:
        if self.pfield == bytes():
            return 0
        return (self.pfield[0] >> 4) & 0b111


class CdsShortTimestamp(CcsdsTimeCode):
    """Unpacks the time datafield of the TM packet. Right now, CDS Short timeformat is used,
    and the size of the time stamp is expected to be seven bytes.
    """

    CDS_SHORT_ID = 0b100
    TIMESTAMP_SIZE = 7

    def __init__(self, ccsds_days: int, ms_of_day: int):
        self.__p_field = bytes([CdsShortTimestamp.CDS_SHORT_ID << 4])
        # CCSDS recommends a 1958 Januar 1 epoch, which is different from the Unix epoch
        self._ccsds_days = ccsds_days
        self._unix_seconds = 0
        self._ms_of_day = ms_of_day
        self._calculate_unix_seconds()
        self._time_string = ""
        self._calculate_time_string()

    def _calculate_unix_seconds(self):
        unix_days = convert_ccsds_days_to_unix_days(self._ccsds_days)
        self._unix_seconds = unix_days * (24 * 60 * 60)
        seconds_of_day = self._ms_of_day / 1000.0
        self._unix_seconds += seconds_of_day

    def _calculate_time_string(self):
        if self._unix_seconds < 0:
            date = datetime.datetime(1970, 1, 1) + datetime.timedelta(
                seconds=self._unix_seconds
            )
        else:
            date = datetime.datetime.utcfromtimestamp(self._unix_seconds)
        self._time_string = date.strftime("%Y-%m-%d %H:%M:%S.%f")

    @property
    def pfield(self) -> bytes:
        return self.__p_field

    @property
    def len(self) -> int:
        return CdsShortTimestamp.TIMESTAMP_SIZE

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
    def __empty(cls):
        return cls(ccsds_days=0, ms_of_day=0)

    @classmethod
    def unpack(cls, time_field: bytes) -> CdsShortTimestamp:
        if len(time_field) < cls.TIMESTAMP_SIZE:
            raise ValueError
        # TODO: check ID?
        p_field = time_field[0]
        ccsds_days = (time_field[1] << 8) | (time_field[2])
        ms_of_day = (
            (time_field[3] << 24)
            | (time_field[4] << 16)
            | (time_field[5]) << 8
            | time_field[6]
        )
        return cls(ccsds_days=ccsds_days, ms_of_day=ms_of_day)

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(ccsds_days={self._ccsds_days!r}, "
            f"ms_of_day={self._ms_of_day!r})"
        )

    def __str__(self):
        return f"Date: {self._time_string} with representation {self!r}"

    @classmethod
    def from_current_time(cls) -> CdsShortTimestamp:
        """Returns a seven byte CDS short timestamp with the current time"""
        return cls.from_unix_days(
            unix_days=(datetime.datetime.utcnow() - UNIX_EPOCH).days,
            ms_of_day=cls.ms_of_day()
        )

    @staticmethod
    def ms_of_day(seconds_since_epoch: Optional[float] = None):
        if seconds_since_epoch is None:
            seconds_since_epoch = time.time()
        fraction_ms = seconds_since_epoch - math.floor(seconds_since_epoch)
        return int(math.floor((seconds_since_epoch % SECONDS_PER_DAY) * 1000 + fraction_ms))

    def as_unix_seconds(self) -> int:
        return self._unix_seconds

    def as_time_string(self) -> str:
        return self._time_string
