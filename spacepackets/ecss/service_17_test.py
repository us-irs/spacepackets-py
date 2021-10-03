from __future__ import annotations
from tmtccmd.pus.service_list import PusServices
from spacepackets.ecss.tm import CdsShortTimestamp, PusVersion, PusTelemetry
from tmtccmd.tm.base import PusTmInfoBase, PusTmBase


class Service17TM:
    def __init__(
            self, subservice_id: int, time: CdsShortTimestamp = None, ssc: int = 0,
            source_data: bytearray = bytearray([]), apid: int = -1, packet_version: int = 0b000,
            pus_version: PusVersion = PusVersion.GLOBAL_CONFIG, pus_tm_version: int = 0b0001,
            ack: int = 0b1111, secondary_header_flag: bool = True, space_time_ref: int = 0b0000,
            destination_id: int = 0
    ):
        self.pus_tm = PusTelemetry(
            service_id=PusServices.SERVICE_17_TEST,
            subservice_id=subservice_id,
            time=time,
            ssc=ssc,
            source_data=source_data,
            apid=apid,
            packet_version=packet_version,
            pus_version=pus_version,
            pus_tm_version=pus_tm_version,
            ack=ack,
            secondary_header_flag=secondary_header_flag,
            space_time_ref=space_time_ref,
            destination_id=destination_id
        )

    @classmethod
    def __empty(cls) -> Service17TM:
        return cls(
            subservice_id=0
        )

    @classmethod
    def unpack(
            cls, raw_telemetry: bytearray, pus_version: PusVersion = PusVersion.GLOBAL_CONFIG
    ) -> Service17TM:
        service_17_tm = cls.__empty()
        service_17_tm.pus_tm = PusTelemetry.unpack(
            raw_telemetry=raw_telemetry, pus_version=pus_version
        )
        return service_17_tm