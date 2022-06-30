from __future__ import annotations
import enum
from spacepackets.ecss.defs import PusServices
from spacepackets.ecss.tm import CdsShortTimestamp, PusVersion, PusTelemetry


class Subservices(enum.IntEnum):
    TC_PING = 1
    TM_REPLY = 2


class Service17Tm:
    def __init__(
        self,
        subservice: int,
        time: CdsShortTimestamp = None,
        ssc: int = 0,
        source_data: bytearray = bytearray([]),
        apid: int = -1,
        packet_version: int = 0b000,
        pus_version: PusVersion = PusVersion.GLOBAL_CONFIG,
        secondary_header_flag: bool = True,
        space_time_ref: int = 0b0000,
        destination_id: int = 0,
    ):
        self.pus_tm = PusTelemetry(
            service=PusServices.S17_TEST,
            subservice=subservice,
            time=time,
            seq_count=ssc,
            source_data=source_data,
            apid=apid,
            packet_version=packet_version,
            secondary_header_flag=secondary_header_flag,
            space_time_ref=space_time_ref,
            destination_id=destination_id,
        )

    def pack(self) -> bytearray:
        return self.pus_tm.pack()

    @classmethod
    def __empty(cls) -> Service17Tm:
        return cls(subservice=0)

    @classmethod
    def unpack(
        cls,
        raw_telemetry: bytearray,
        pus_version: PusVersion = PusVersion.GLOBAL_CONFIG,
    ) -> Service17Tm:
        service_17_tm = cls.__empty()
        service_17_tm.pus_tm = PusTelemetry.unpack(raw_telemetry=raw_telemetry)
        return service_17_tm
