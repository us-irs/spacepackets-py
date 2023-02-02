from __future__ import annotations

import struct

from spacepackets import BytesTooShortError
from spacepackets.ccsds.spacepacket import PacketId, PacketSeqCtrl, SpacePacketHeader
from spacepackets.ecss.tc import PusTelecommand


class RequestId:
    """The request ID which is used to identify PUS telecommands. The request ID consists of
    the first two bytes of the CCSDS primary header. It is primarily used to verify the execution
    of sent telecommands.

    >>> from spacepackets.ccsds import PacketType, SequenceFlags
    >>> packet_id = PacketId(ptype=PacketType.TC, sec_header_flag=False, apid=0x22)
    >>> psc = PacketSeqCtrl(seq_flags=SequenceFlags.UNSEGMENTED, seq_count=17)
    >>> req_id = RequestId(packet_id, psc)
    >>> req_id
    RequestId(tc_packet_id=PacketId(ptype=<PacketType.TC: 1>, sec_header_flag=False, apid=34), \
tc_psc=PacketSeqCtrl(seq_flags=<SequenceFlags.UNSEGMENTED: 3>, seq_count=17), ccsds_version=0)
    >>> struct.pack("!I", req_id.as_u32()).hex(sep=",")
    '10,22,c0,11'
    """

    def __init__(
        self, tc_packet_id: PacketId, tc_psc: PacketSeqCtrl, ccsds_version: int = 0b000
    ):
        self.tc_packet_id = tc_packet_id
        self.tc_psc = tc_psc
        self.ccsds_version = ccsds_version

    @classmethod
    def empty(cls):
        return cls(PacketId.empty(), PacketSeqCtrl.empty())

    @classmethod
    def unpack(cls, tm_data: bytes) -> RequestId:
        if len(tm_data) < 4:
            raise BytesTooShortError(4, len(tm_data))
        packet_id_version_raw = struct.unpack("!H", tm_data[0:2])[0]
        psc_raw = struct.unpack("!H", tm_data[2:4])[0]
        return cls(
            ccsds_version=(packet_id_version_raw >> 13) & 0b111,
            tc_packet_id=PacketId.from_raw(packet_id_version_raw),
            tc_psc=PacketSeqCtrl.from_raw(psc_raw),
        )

    @classmethod
    def from_pus_tc(cls, pus_tc: PusTelecommand):
        return cls.from_sp_header(pus_tc.sp_header)

    @classmethod
    def from_sp_header(cls, header: SpacePacketHeader) -> RequestId:
        return cls(
            ccsds_version=header.ccsds_version,
            tc_packet_id=header.packet_id,
            tc_psc=header.psc,
        )

    def pack(self) -> bytes:
        raw = bytearray()
        packet_id_and_version = (self.ccsds_version << 13) | self.tc_packet_id.raw()
        raw.extend(struct.pack("!H", packet_id_and_version))
        raw.extend(struct.pack("!H", self.tc_psc.raw()))
        return raw

    def as_u32(self):
        packet_id_and_version = (self.ccsds_version << 13) | self.tc_packet_id.raw()
        return (packet_id_and_version << 16) | self.tc_psc.raw()

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(tc_packet_id={self.tc_packet_id!r}, "
            f"tc_psc={self.tc_psc!r}, ccsds_version={self.ccsds_version!r})"
        )

    def __str__(self):
        return f"Request ID: [{self.tc_packet_id}, {self.tc_psc}]"

    def __eq__(self, other: RequestId):
        return self.as_u32() == other.as_u32()

    def __hash__(self):
        return self.as_u32().__hash__()
