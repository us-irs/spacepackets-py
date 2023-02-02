from __future__ import annotations
import enum
from typing import Optional

from spacepackets import SpacePacketHeader
from spacepackets.ccsds.time import CcsdsTimeProvider
from spacepackets.ecss.conf import FETCH_GLOBAL_APID
from spacepackets.ecss.defs import PusService
from spacepackets.ecss.tm import PusTelemetry, AbstractPusTm


class Subservice(enum.IntEnum):
    TC_PING = 1
    TM_REPLY = 2


class Service17Tm(AbstractPusTm):
    def __init__(
        self,
        subservice: int,
        time_provider: Optional[CcsdsTimeProvider],
        ssc: int = 0,
        source_data: bytes = bytes(),
        apid: int = FETCH_GLOBAL_APID,
        packet_version: int = 0b000,
        space_time_ref: int = 0b0000,
        destination_id: int = 0,
    ):
        self.pus_tm = PusTelemetry(
            service=PusService.S17_TEST,
            subservice=subservice,
            time_provider=time_provider,
            seq_count=ssc,
            source_data=source_data,
            apid=apid,
            packet_version=packet_version,
            space_time_ref=space_time_ref,
            destination_id=destination_id,
        )

    @property
    def sp_header(self) -> SpacePacketHeader:
        return self.pus_tm.space_packet_header

    @property
    def service(self) -> int:
        return self.pus_tm.service

    @property
    def time_provider(self) -> Optional[CcsdsTimeProvider]:
        return self.pus_tm.time_provider

    @property
    def subservice(self) -> int:
        return self.pus_tm.subservice

    @property
    def source_data(self) -> bytes:
        return self.pus_tm.source_data

    def pack(self) -> bytearray:
        return self.pus_tm.pack()

    @classmethod
    def __empty(cls, time_provider: Optional[CcsdsTimeProvider]) -> Service17Tm:
        return cls(subservice=0, time_provider=time_provider)

    @classmethod
    def unpack(
        cls, data: bytes, time_reader: Optional[CcsdsTimeProvider]
    ) -> Service17Tm:
        """

        :raises BytesTooShortError: Passed bytestream too short.
        :raises ValueError: Unsupported PUS version.
        :raises InvalidTmCrc16: Invalid CRC16.
        """
        service_17_tm = cls.__empty(time_provider=time_reader)
        service_17_tm.pus_tm = PusTelemetry.unpack(data=data, time_reader=time_reader)
        return service_17_tm
