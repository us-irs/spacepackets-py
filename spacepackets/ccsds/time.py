from __future__ import annotations
import datetime
import math
import enum
import time
from abc import abstractmethod

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


class CcsdsTimeCode:
    @abstractmethod
    def pack(self) -> bytearray:
        self.ccsds_id = CcsdsTimeCodeId.NONE
        return bytearray()

    @abstractmethod
    def return_unix_seconds(self) -> int:
        return 0

    @abstractmethod
    def return_time_string(self) -> str:
        return ""


class CdsShortTimestamp(CcsdsTimeCode):
    """Unpacks the time datafield of the TM packet. Right now, CDS Short timeformat is used,
    and the size of the time stamp is expected to be seven bytes.
    """

    CDS_SHORT_ID = 0b100
    TIMESTAMP_SIZE = 7

    def __init__(self, ccsds_days: int, ms_of_day: int):
        self.ccsds_id = CcsdsTimeCodeId.CDS
        self.p_field = CdsShortTimestamp.CDS_SHORT_ID << 4
        # CCSDS recommends a 1958 Januar 1 epoch, which is different from the Unix epoch
        self.ccsds_days = ccsds_days
        self.unix_days = convert_ccsds_days_to_unix_days(self.ccsds_days)
        self.unix_seconds = self.unix_days * (24 * 60 * 60)
        self.ms_of_day = ms_of_day
        self.seconds_of_day = self.ms_of_day / 1000.0
        self.unix_seconds += self.seconds_of_day
        if self.unix_seconds < 0:
            date = datetime.datetime(1970, 1, 1) + datetime.timedelta(
                seconds=self.unix_seconds
            )
        else:
            date = datetime.datetime.utcfromtimestamp(self.unix_seconds)
        self.time_string = date.strftime("%Y-%m-%d %H:%M:%S.%f")

    @classmethod
    def init_from_unix_days(cls, unix_days: int, ms_of_day: int) -> CdsShortTimestamp:
        return cls(
            ccsds_days=convert_unix_days_to_ccsds_days(unix_days=unix_days),
            ms_of_day=ms_of_day,
        )

    @classmethod
    def __empty(cls):
        return cls(ccsds_days=0, ms_of_day=0)

    def pack(self) -> bytearray:
        cds_packet = bytearray()
        cds_packet.append(self.p_field)
        cds_packet.append((self.ccsds_days & 0xFF00) >> 8)
        cds_packet.append(self.ccsds_days & 0xFF)
        cds_packet.append((self.ms_of_day & 0xFF000000) >> 24)
        cds_packet.append((self.ms_of_day & 0x00FF0000) >> 16)
        cds_packet.append((self.ms_of_day & 0x0000FF00) >> 8)
        cds_packet.append(self.ms_of_day & 0x000000FF)
        return cds_packet

    @classmethod
    def unpack(cls, time_field: bytearray) -> CdsShortTimestamp:
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

    @staticmethod
    def init_from_current_time() -> CdsShortTimestamp:
        """Returns a seven byte CDS short timestamp with the current time"""
        unix_days = (datetime.datetime.utcnow() - UNIX_EPOCH).days
        seconds = time.time()
        fraction_ms = seconds - math.floor(seconds)
        days_ms = int((seconds % SECONDS_PER_DAY) * 1000 + fraction_ms)
        time_packet = CdsShortTimestamp.init_from_unix_days(
            unix_days=unix_days, ms_of_day=days_ms
        )
        return time_packet

    @abstractmethod
    def return_unix_seconds(self) -> int:
        return self.unix_seconds

    @abstractmethod
    def return_time_string(self) -> str:
        return self.time_string
