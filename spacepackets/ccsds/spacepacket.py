from __future__ import annotations
import enum

from typing import Tuple, Deque, List, Final
from spacepackets.log import get_console_logger

SPACE_PACKET_HEADER_SIZE: Final = 6


class PacketTypes(enum.IntEnum):
    TM = 0
    TC = 1


class SequenceFlags(enum.IntEnum):
    CONTINUATION_SEGMENT = 0b00
    FIRST_SEGMENT = 0b01
    LAST_SEGMENT = 0b10
    UNSEGMENTED = 0b11


class SpacePacketHeader:
    """This class encapsulates the space packet header.
    Packet reference: Blue Book CCSDS 133.0-B-2"""

    def __init__(
        self,
        packet_type: PacketTypes,
        apid: int,
        source_sequence_count: int,
        data_length: int,
        packet_version: int = 0b000,
        secondary_header_flag: bool = True,
        sequence_flags: SequenceFlags = SequenceFlags.UNSEGMENTED,
    ):
        """Create a space packet header with the given field parameters

        :param packet_type: 0 for Telemetery, 1 for Telecommands
        :param apid: Application Process ID, should not be larger
            than 11 bits, deciaml 2074 or hex 0x7ff
        :param source_sequence_count: Sequence counter, should not be larger than 0x3fff or
            decimal 16383
        :param data_length: Should not be largen than 65535 bytes
        :param packet_version:
        :param secondary_header_flag:
        :param sequence_flags:
        :raises ValueError: On invalid parameters
        """
        self.packet_type = packet_type
        if apid > pow(2, 11) - 1 or apid < 0:
            logger = get_console_logger()
            logger.warning(
                f"Invalid APID, exceeds maximum value {pow(2, 11) - 1} or negative"
            )
            raise ValueError
        if source_sequence_count > pow(2, 14) - 1 or source_sequence_count < 0:
            logger = get_console_logger()
            logger.warning(
                f"Invalid source sequence count, exceeds maximum value {pow(2, 14)- 1} or negative"
            )
            raise ValueError
        if data_length > pow(2, 16) - 1 or data_length < 0:
            logger = get_console_logger()
            logger.warning(
                f"Invalid data length value, exceeds maximum value of {pow(2, 16) - 1} or negative"
            )
            raise ValueError
        self.apid = apid
        self.ssc = source_sequence_count
        self.secondary_header_flag = secondary_header_flag
        self.sequence_flags = sequence_flags
        self.psc = get_space_packet_sequence_control(
            sequence_flags=self.sequence_flags, source_sequence_count=self.ssc
        )
        self.version = packet_version
        self.data_length = data_length
        self.packet_id = get_space_packet_id_num(
            packet_type=self.packet_type,
            secondary_header_flag=self.secondary_header_flag,
            apid=self.apid,
        )

    def pack(self) -> bytearray:
        """Serialize raw space packet header into a bytearray"""
        header = bytearray()
        header.append((self.packet_id & 0xFF00) >> 8)
        header.append(self.packet_id & 0xFF)
        header.append((self.psc & 0xFF00) >> 8)
        header.append(self.psc & 0xFF)
        header.append((self.data_length & 0xFF00) >> 8)
        header.append(self.data_length & 0xFF)
        return header

    @property
    def header_len(self) -> int:
        return SPACE_PACKET_HEADER_SIZE

    @property
    def packet_len(self) -> int:
        """Retrieve the full space packet size when packed
        :return: Size of the TM packet based on the space packet header data length field.
        The space packet data field is the full length of data field minus one without
        the space packet header.
        """
        return SPACE_PACKET_HEADER_SIZE + self.data_length + 1

    @classmethod
    def unpack(cls, space_packet_raw: bytes) -> SpacePacketHeader:
        """Unpack a raw space packet into the space packet header instance
        :raise ValueError: Raw packet length invalid
        """
        if len(space_packet_raw) < SPACE_PACKET_HEADER_SIZE:
            logger = get_console_logger()
            logger.warning("Packet size smaller than PUS header size!")
            raise ValueError
        packet_type = space_packet_raw[0] & 0x10
        if packet_type == 0:
            packet_type = PacketTypes.TM
        else:
            packet_type = PacketTypes.TC
        packet_version = space_packet_raw[0] >> 5
        secondary_header_flag = (space_packet_raw[0] & 0x8) >> 3
        apid = ((space_packet_raw[0] & 0x7) << 8) | space_packet_raw[1]
        sequence_flags = (space_packet_raw[2] & 0xC0) >> 6
        ssc = ((space_packet_raw[2] << 8) | space_packet_raw[3]) & 0x3FFF
        data_length = space_packet_raw[4] << 8 | space_packet_raw[5]
        return SpacePacketHeader(
            packet_type=packet_type,
            apid=apid,
            secondary_header_flag=bool(secondary_header_flag),
            packet_version=packet_version,
            data_length=data_length,
            sequence_flags=SequenceFlags(sequence_flags),
            source_sequence_count=ssc,
        )

    def __str__(self):
        return (
            f"Space Packet with Packet ID 0x{self.packet_id:04x}, APID {self.apid}, "
            f"SSC {self.ssc}, Data Length {self.data_length}"
        )

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(packet_type={self.packet_type!r}, "
            f"packet_id={self.packet_id!r}, apid={self.apid!r}, ssc={self.ssc!r})"
        )


def get_space_packet_id_bytes(
    packet_type: PacketTypes,
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


def get_space_packet_id_num(
    packet_type: PacketTypes, secondary_header_flag: bool, apid: int
) -> int:
    """Get packet identification segment of packet primary header in integer format"""
    return (packet_type << 12 | int(secondary_header_flag) << 11 | apid) & 0x1FFF


def get_space_packet_sequence_control(
    sequence_flags: SequenceFlags, source_sequence_count: int
) -> int:
    """Get sequence control in integer format"""
    if sequence_flags > SequenceFlags.UNSEGMENTED:
        logger = get_console_logger()
        logger.warning("Sequence flag value larger than 0b11")
        raise ValueError
    if source_sequence_count > 0x3FFF:
        logger = get_console_logger()
        logger.warning(
            "get_sp_packet_sequence_control: Source sequence count largen than 0x3fff"
        )
        raise ValueError
    return (source_sequence_count & 0x3FFF) | (sequence_flags << 14)


def get_space_packet_header(
    packet_id: int, packet_sequence_control: int, data_length: int
) -> bytearray:
    """Retrieve raw space packet header from the three required values"""
    header = bytearray()
    header.append((packet_id & 0xFF00) >> 8)
    header.append(packet_id & 0xFF)
    header.append((packet_sequence_control & 0xFF00) >> 8)
    header.append(packet_sequence_control & 0xFF)
    header.append((data_length & 0xFF00) >> 8)
    header.append(data_length & 0xFF)
    return header


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
    analysis_queue: Deque[bytearray], packet_ids: Tuple[int]
) -> List[bytearray]:
    """Given a deque of bytearrays, parse for space packets. Any broken headers will be removed.
    If a packet is detected and the
    Any broken tail packets will be reinserted into the given deque
    :param analysis_queue:
    :param packet_ids:
    :return:
    """
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
        if current_idx + 1 >= len(concatenated_packets):
            break
        current_packet_id = (
            concatenated_packets[current_idx] << 8
        ) | concatenated_packets[current_idx + 1]
        if current_packet_id in packet_ids:
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
    next_packet_len_field = (
        concatenated_packets[current_idx + 4] | concatenated_packets[current_idx + 5]
    )
    total_packet_len = get_total_space_packet_len_from_len_field(next_packet_len_field)
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
