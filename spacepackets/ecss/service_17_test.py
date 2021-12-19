from __future__ import annotations

from spacepackets.ecss.definitions import PusServices
from spacepackets.ecss.tm import CdsShortTimestamp, PusVersion, PusTelemetry


class Service17TM:
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
            service=PusServices.SERVICE_17_TEST,
            subservice=subservice,
            time=time,
            ssc=ssc,
            source_data=source_data,
            apid=apid,
            packet_version=packet_version,
            pus_version=pus_version,
            secondary_header_flag=secondary_header_flag,
            space_time_ref=space_time_ref,
            destination_id=destination_id,
        )

    def pack(self) -> bytearray:
        return self.pus_tm.pack()

    @classmethod
    def __empty(cls) -> Service17TM:
        return cls(subservice=0)

    @classmethod
    def unpack(
        cls,
        raw_telemetry: bytearray,
        pus_version: PusVersion = PusVersion.GLOBAL_CONFIG,
    ) -> Service17TM:
        service_17_tm = cls.__empty()
        service_17_tm.pus_tm = PusTelemetry.unpack(
            raw_telemetry=raw_telemetry, pus_version=pus_version
        )
        return service_17_tm
