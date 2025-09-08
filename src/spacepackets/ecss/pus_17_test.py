from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from spacepackets.ecss.defs import PusService
from spacepackets.ecss.tm import AbstractPusTm, MiscParams, PusTm

if TYPE_CHECKING:
    from spacepackets import SpacePacketHeader
    from spacepackets.ccsds.spacepacket import PacketId, PacketSeqCtrl


class Subservice(enum.IntEnum):
    TC_PING = 1
    TM_REPLY = 2


class Service17Tm(AbstractPusTm):
    def __init__(
        self,
        apid: int,
        subservice: int,
        timestamp: bytes,
        ssc: int = 0,
        source_data: bytes = b"",
        destination_id: int = 0,
        misc_params: MiscParams | None = None,
    ):
        self.pus_tm = PusTm(
            service=PusService.S17_TEST,
            subservice=subservice,
            timestamp=timestamp,
            seq_count=ssc,
            source_data=source_data,
            apid=apid,
            destination_id=destination_id,
            misc_params=misc_params,
        )

    @property
    def sp_header(self) -> SpacePacketHeader:
        return self.pus_tm.space_packet_header

    @property
    def ccsds_version(self) -> int:
        return self.pus_tm.ccsds_version

    @property
    def packet_id(self) -> PacketId:
        return self.pus_tm.packet_id

    @property
    def packet_seq_control(self) -> PacketSeqCtrl:
        return self.pus_tm.packet_seq_control

    @property
    def service(self) -> int:
        return self.pus_tm.service

    @property
    def timestamp(self) -> bytes:
        return self.pus_tm.timestamp

    @property
    def subservice(self) -> int:
        return self.pus_tm.subservice

    @property
    def source_data(self) -> bytes:
        return self.pus_tm.source_data

    def pack(self) -> bytearray:
        return self.pus_tm.pack()

    @classmethod
    def __empty(cls) -> Service17Tm:
        return cls(apid=0, subservice=0, timestamp=b"")

    @classmethod
    def unpack(cls, data: bytes | bytearray, timestamp_len: int) -> Service17Tm:
        """

        :raises BytesTooShortError: Passed bytestream too short.
        :raises ValueError: Unsupported PUS version.
        :raises InvalidTmCrc16: Invalid CRC16.
        """
        service_17_tm = cls.__empty()
        service_17_tm.pus_tm = PusTm.unpack(data=data, timestamp_len=timestamp_len)
        return service_17_tm
