"""This module also includes the :py:class:`SpacePacketHeader` class, which is the header component
of all CCSDS packets."""
from __future__ import annotations

from abc import abstractmethod, ABC
import enum
import struct

from typing import Tuple, Deque, List, Final, Optional, Sequence

from spacepackets.exceptions import BytesTooShortError

SPACE_PACKET_HEADER_SIZE: Final = 6
SEQ_FLAG_MASK = 0xC000
APID_MASK = 0x7FF
PACKET_ID_MASK = 0x1FFF


class PacketType(enum.IntEnum):
    TM = 0
    TC = 1


class SequenceFlags(enum.IntEnum):
    CONTINUATION_SEGMENT = 0b00
    FIRST_SEGMENT = 0b01
    LAST_SEGMENT = 0b10
    UNSEGMENTED = 0b11


class PacketSeqCtrl:
    """The packet sequence control is the third and fourth byte of the space packet header.
    It contains the sequence flags and the 14-bit sequence count.
    """

    def __init__(self, seq_flags: SequenceFlags, seq_count: int):
        if seq_count > pow(2, 14) - 1 or seq_count < 0:
            raise ValueError(
                f"Sequence count larger than allowed {pow(2, 14) - 1} or negative"
            )
        self.seq_flags = seq_flags
        self.seq_count = seq_count

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(seq_flags={self.seq_flags!r}, "
            f"seq_count={self.seq_count!r})"
        )

    def __str__(self):
        if self.seq_flags == SequenceFlags.CONTINUATION_SEGMENT:
            seqstr = "CONT"
        elif self.seq_flags == SequenceFlags.LAST_SEGMENT:
            seqstr = "FIRST"
        elif self.seq_flags == SequenceFlags.LAST_SEGMENT:
            seqstr = "LAST"
        elif self.seq_flags == SequenceFlags.UNSEGMENTED:
            seqstr = "UNSEG"
        else:
            raise ValueError("Invalid sequence flag")
        return f"PSC: [Seq Flags: {seqstr}, Seq Count: {self.seq_count}]"

    def raw(self) -> int:
        return self.seq_flags << 14 | self.seq_count

    @classmethod
    def empty(cls):
        return cls(seq_flags=SequenceFlags.CONTINUATION_SEGMENT, seq_count=0)

    @classmethod
    def from_raw(cls, raw: int):
        return cls(
            seq_flags=SequenceFlags((raw >> 14) & 0b11), seq_count=raw & ~SEQ_FLAG_MASK
        )


class PacketId:
    """The packet ID forms the last thirteen bits of the first two bytes of the
    space packet header."""

    def __init__(self, ptype: PacketType, sec_header_flag: bool, apid: int):
        if apid > pow(2, 11) - 1 or apid < 0:
            raise ValueError(
                f"Invalid APID, exceeds maximum value {pow(2, 11) - 1} or negative"
            )
        self.ptype = ptype
        self.sec_header_flag = sec_header_flag
        self.apid = apid

    @classmethod
    def empty(cls):
        return cls(ptype=PacketType.TM, sec_header_flag=False, apid=0)

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(ptype={self.ptype!r}, "
            f"sec_header_flag={self.sec_header_flag!r}, apid={self.apid!r})"
        )

    def __str__(self):
        pstr = "TM" if self.ptype == PacketType.TM else "TC"
        return (
            f"Packet ID: [Packet Type: {pstr}, Sec Header Flag: {self.sec_header_flag}, "
            f"APID: {self.apid:#05x}]"
        )

    def raw(self) -> int:
        return self.ptype << 12 | self.sec_header_flag << 11 | self.apid

    @classmethod
    def from_raw(cls, raw: int) -> PacketId:
        return cls(
            ptype=PacketType((raw >> 12) & 0b1),
            sec_header_flag=bool(raw >> 11 & 0b1),
            apid=raw & APID_MASK,
        )


class AbstractSpacePacket(ABC):
    @property
    @abstractmethod
    def apid(self) -> int:
        pass

    @property
    @abstractmethod
    def seq_count(self) -> int:
        pass


class SpacePacketHeader(AbstractSpacePacket):
    """This class encapsulates the space packet header.
    Packet reference: Blue Book CCSDS 133.0-B-2"""

    def __init__(
        self,
        packet_type: PacketType,
        apid: int,
        seq_count: int,
        data_len: int,
        sec_header_flag: bool = False,
        seq_flags: SequenceFlags = SequenceFlags.UNSEGMENTED,
        ccsds_version: int = 0b000,
    ):
        """Create a space packet header with the given field parameters.

        >>> sph = SpacePacketHeader(packet_type=PacketType.TC, apid=0x42, seq_count=0, data_len=12)
        >>> hex(sph.apid)
        '0x42'
        >>> sph.packet_type
        <PacketType.TC: 1>
        >>> sph.data_len
        12
        >>> sph.packet_len
        19
        >>> sph.packet_id
        PacketId(ptype=<PacketType.TC: 1>, sec_header_flag=False, apid=66)
        >>> sph.psc
        PacketSeqCtrl(seq_flags=<SequenceFlags.UNSEGMENTED: 3>, seq_count=0)

        :param packet_type: 0 for Telemetery, 1 for Telecommands
        :param apid: Application Process ID, should not be larger
            than 11 bits, deciaml 2074 or hex 0x7ff
        :param seq_count: Source sequence counter, should not be larger than 0x3fff or
            decimal 16383
        :param data_len: Contains a length count C that equals one fewer than the length of the
            packet data field. Should not be larger than 65535 bytes
        :param ccsds_version:
        :param sec_header_flag: Secondary header flag, 1 or True by default
        :param seq_flags:
        :raises ValueError: On invalid parameters
        """
        if data_len > pow(2, 16) - 1 or data_len < 0:
            raise ValueError(
                f"Invalid data length value, exceeds maximum value of {pow(2, 16) - 1} or negative"
            )
        self.ccsds_version = ccsds_version
        self.packet_id = PacketId(
            ptype=packet_type, sec_header_flag=sec_header_flag, apid=apid
        )
        self.psc = PacketSeqCtrl(seq_flags=seq_flags, seq_count=seq_count)
        self.data_len = data_len

    @classmethod
    def from_composite_fields(
        cls,
        packet_id: PacketId,
        psc: PacketSeqCtrl,
        data_length: int,
        packet_version: int = 0b000,
    ) -> SpacePacketHeader:
        return SpacePacketHeader(
            packet_type=packet_id.ptype,
            ccsds_version=packet_version,
            sec_header_flag=packet_id.sec_header_flag,
            data_len=data_length,
            seq_flags=psc.seq_flags,
            seq_count=psc.seq_count,
            apid=packet_id.apid,
        )

    def pack(self) -> bytearray:
        """Serialize raw space packet header into a bytearray, using big endian for each
        2 octet field of the space packet header."""
        header = bytearray()
        packet_id_with_version = self.ccsds_version << 13 | self.packet_id.raw()
        header.extend(struct.pack("!H", packet_id_with_version))
        header.extend(struct.pack("!H", self.psc.raw()))
        header.extend(struct.pack("!H", self.data_len))
        return header

    @property
    def packet_type(self):
        return self.packet_id.ptype

    @packet_type.setter
    def packet_type(self, packet_type):
        self.packet_id.ptype = packet_type

    @property
    def apid(self):
        return self.packet_id.apid

    @property
    def sec_header_flag(self):
        return self.packet_id.sec_header_flag

    @sec_header_flag.setter
    def sec_header_flag(self, value):
        self.packet_id.sec_header_flag = value

    @property
    def seq_count(self):
        return self.psc.seq_count

    @seq_count.setter
    def seq_count(self, seq_cnt):
        self.psc.seq_count = seq_cnt

    @property
    def seq_flags(self):
        return self.psc.seq_flags

    @seq_flags.setter
    def seq_flags(self, value):
        self.psc.seq_flags = value

    @property
    def header_len(self) -> int:
        return SPACE_PACKET_HEADER_SIZE

    @apid.setter
    def apid(self, apid):
        self.packet_id.apid = apid

    @property
    def packet_len(self) -> int:
        """Retrieve the full space packet size when packed.

        :return: Size of the TM packet based on the space packet header data length field.
        """
        return SPACE_PACKET_HEADER_SIZE + self.data_len + 1

    @classmethod
    def unpack(cls, data: bytes) -> SpacePacketHeader:
        """Unpack a raw space packet into the space packet header instance.

        :raise ValueError: Raw packet length invalid
        """
        if len(data) < SPACE_PACKET_HEADER_SIZE:
            raise BytesTooShortError(SPACE_PACKET_HEADER_SIZE, len(data))
        packet_version = (data[0] >> 5) & 0b111
        packet_type = PacketType((data[0] >> 4) & 0b1)
        secondary_header_flag = (data[0] >> 3) & 0b1
        apid = ((data[0] & 0b111) << 8) | data[1]
        psc = struct.unpack("!H", data[2:4])[0]
        sequence_flags = (psc & SEQ_FLAG_MASK) >> 14
        ssc = psc & (~SEQ_FLAG_MASK)
        return SpacePacketHeader(
            packet_type=packet_type,
            apid=apid,
            sec_header_flag=bool(secondary_header_flag),
            ccsds_version=packet_version,
            data_len=struct.unpack("!H", data[4:6])[0],
            seq_flags=SequenceFlags(sequence_flags),
            seq_count=ssc,
        )

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(packet_version={self.ccsds_version!r}, "
            f"packet_type={self.packet_type!r}, apid={self.apid!r}, seq_cnt={self.seq_count!r}, "
            f"data_len={self.data_len!r}, sec_header_flag={self.sec_header_flag!r}, "
            f"seq_flags={self.seq_flags!r})"
        )

    def __eq__(self, other: SpacePacketHeader):
        return self.pack() == other.pack()


class SpacePacket:
    """Generic CCSDS space packet which consists of the primary header and can optionally include
    a secondary header and a user data field.

    If the secondary header flag in the primary header is set, the secondary header in mandatory.
    If it is not set, the user data is mandatory."""

    def __init__(
        self,
        sp_header: SpacePacketHeader,
        sec_header: Optional[bytes],
        user_data: Optional[bytes],
    ):
        self.sp_header = sp_header
        self.sec_header = sec_header
        self.user_data = user_data

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(sp_header={self.sp_header!r}, "
            f"sec_header={self.sec_header!r}, user_data={self.user_data!r})"
        )

    def pack(self) -> bytearray:
        """Pack the raw byte representation of the space packet
        :raises ValueError: Mandatory fields were not supplied properly"""
        packet = self.sp_header.pack()
        if self.sp_header.sec_header_flag:
            if self.sec_header is None:
                raise ValueError(
                    "Secondary header flag is set but no secondary header was supplied"
                )
            packet.extend(self.sec_header)
        else:
            if self.user_data is None:
                raise ValueError(
                    "Secondary header not present but no user data supplied"
                )
        if self.user_data is not None:
            packet.extend(self.user_data)
        return packet

    @property
    def apid(self):
        return self.sp_header.apid

    @property
    def seq_count(self):
        return self.sp_header.seq_count

    @property
    def sec_header_flag(self):
        return self.sp_header.sec_header_flag

    def __eq__(self, other: SpacePacket):
        return (
            self.sp_header == other.sp_header
            and self.sec_header == other.sec_header
            and self.user_data == other.user_data
        )


def get_space_packet_id_bytes(
    packet_type: PacketType,
    secondary_header_flag: True,
    apid: int,
    version: int = 0b000,
) -> Tuple[int, int]:
    """This function also includes the first three bits reserved for the version.

    :param version: Version field of the packet ID. Defined to be 0b000 in the space packet standard
    :param packet_type: 0 for TM, 1 for TC
    :param secondary_header_flag: Indicates presence of absence of a Secondary Header
        in the Space Packet
    :param apid: Application Process Identifier. Naming mechanism for managed data path, has 11 bits
    :return:
    """
    byte_one = (
        ((version << 5) & 0xE0)
        | ((packet_type & 0x01) << 4)
        | ((int(secondary_header_flag) & 0x01) << 3)
        | ((apid & 0x700) >> 8)
    )
    byte_two = apid & 0xFF
    return byte_one, byte_two


def get_sp_packet_id_raw(
    packet_type: PacketType, secondary_header_flag: bool, apid: int
) -> int:
    """Get packet identification segment of packet primary header in integer format"""
    return PacketId(packet_type, secondary_header_flag, apid).raw()


def get_sp_psc_raw(seq_flags: SequenceFlags, seq_count: int) -> int:
    return PacketSeqCtrl(seq_flags=seq_flags, seq_count=seq_count).raw()


def get_apid_from_raw_space_packet(raw_packet: bytes) -> int:
    """Retrieve the APID from the raw packet.

    :param raw_packet:
    :raises ValueError: Passed bytearray too short
    :return:
    """
    if len(raw_packet) < 6:
        raise ValueError
    return ((raw_packet[0] & 0x7) << 8) | raw_packet[1]


def get_total_space_packet_len_from_len_field(len_field: int):
    """Definition of length field is: C = (Octets in data field - 1).
    Therefore, octets in data field in len_field plus one. The total space packet length
    is therefore len_field plus one plus the space packet header size (6)"""
    return len_field + SPACE_PACKET_HEADER_SIZE + 1


def parse_space_packets(
    analysis_queue: Deque[bytearray], packet_ids: Sequence[PacketId]
) -> List[bytearray]:
    """Given a deque of bytearrays, parse for space packets. Any broken headers will be removed.
    If a packet is detected and the broken tail packets will be reinserted into the given deque.

    :param analysis_queue:
    :param packet_ids:
    :return:
    """
    ids_raw = [packet_id.raw() for packet_id in packet_ids]
    tm_list = []
    concatenated_packets = bytearray()
    if not analysis_queue:
        return tm_list
    while analysis_queue:
        # Put it all in one buffer
        concatenated_packets.extend(analysis_queue.pop())
    current_idx = 0
    if len(concatenated_packets) < 6:
        return tm_list
    # Packet ID detected
    while True:
        if current_idx + 6 >= len(concatenated_packets):
            break
        current_packet_id = (
            struct.unpack("!H", concatenated_packets[current_idx : current_idx + 2])[0]
            & PACKET_ID_MASK
        )
        if current_packet_id in ids_raw:
            result, current_idx = __handle_packet_id_match(
                concatenated_packets=concatenated_packets,
                analysis_queue=analysis_queue,
                current_idx=current_idx,
                tm_list=tm_list,
            )
            if result != 0:
                break
        else:
            # Keep parsing until a packet ID is found
            current_idx += 1
    return tm_list


def __handle_packet_id_match(
    concatenated_packets: bytearray,
    analysis_queue: Deque[bytearray],
    current_idx: int,
    tm_list: List[bytearray],
) -> (int, int):
    total_packet_len = get_total_space_packet_len_from_len_field(
        struct.unpack("!H", concatenated_packets[current_idx + 4 : current_idx + 6])[0]
    )
    # Might be part of packet. Put back into analysis queue as whole
    if total_packet_len > len(concatenated_packets):
        analysis_queue.appendleft(concatenated_packets)
        return -1, current_idx
    else:
        tm_list.append(
            concatenated_packets[current_idx : current_idx + total_packet_len]
        )
        current_idx += total_packet_len
    return 0, current_idx
