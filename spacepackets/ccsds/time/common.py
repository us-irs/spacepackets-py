from __future__ import annotations
import datetime
import enum
from abc import abstractmethod, ABC

import deprecation
from spacepackets import __version__

#: The day offset to convert from CCSDS days to UNIX days.
DAYS_CCSDS_TO_UNIX = -4383
#: Seconds per days as integer
SECONDS_PER_DAY: int = 86400
#: Milliseconds per day as integer
MS_PER_DAY: int = SECONDS_PER_DAY * 1000
UNIX_EPOCH = datetime.datetime.fromtimestamp(0, tz=datetime.timezone.utc)


class CcsdsTimeCodeId(enum.IntEnum):
    NONE = 0
    CUC_CCSDS_EPOCH = 0b001
    CUC_AGENCY_EPOCH = 0b010
    CDS = 0b100
    CCS = 0b101


def convert_unix_days_to_ccsds_days(unix_days: int) -> int:
    """Convert Unix days to CCSDS days.

    CCSDS epoch: 1958-01-01 00:00:00.
    Unix epoch: 1970-01-01 00:00:00.
    """
    return unix_days - DAYS_CCSDS_TO_UNIX


def convert_ccsds_days_to_unix_days(ccsds_days: int) -> int:
    """Convert CCSDS days to Unix days.

    CCSDS epoch: 1958-01-01 00:00:00.
    Unix epoch: 1970-01-01 00:00:00.
    """
    return ccsds_days + DAYS_CCSDS_TO_UNIX


def read_p_field(p_field: int) -> CcsdsTimeCodeId:
    """Read the p field and return the CCSDS Time Code ID.

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
    def len_packed(self) -> int:
        pass

    @deprecation.deprecated(
        deprecated_in="0.14.0rc1",
        current_version=__version__,
        details="use len_packed instead",
    )
    @property
    def len(self) -> int:
        return self.len_packed

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
        return self.as_date_time()

    @abstractmethod
    def as_date_time(self) -> datetime:
        """Retrieve a :py:class:`datetime.datetime` with the :py:class:`datetime.timezone` set to
        utc.
        """
        pass

    def as_time_string(self) -> str:
        return self.as_date_time().strftime("%Y-%m-%d %H:%M:%S.%f")

    def ccsds_time_code(self) -> int:
        if self.pfield == bytes():
            return 0
        return (self.pfield[0] >> 4) & 0b111


if __name__ == "__main__":
    import doctest

    doctest.testmod()
