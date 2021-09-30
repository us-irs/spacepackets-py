from __future__ import annotations
import enum

from typing import Tuple, Deque, List
from spacepackets.log import get_console_logger

SPACE_PACKET_HEADER_SIZE = 6


class PacketTypes(enum.IntEnum):
    PACKET_TYPE_TM = 0
    PACKET_TYPE_TC = 1


class SequenceFlags(enum.IntEnum):
    CONTINUATION_SEGMENT = 0b00,
    FIRST_SEGMENT = 0b01,
    LAST_SEGMENT = 0b10,
    UNSEGMENTED = 0b11


class SpacePacketHeader:
    """This class encapsulates the space packet header. Packet reference: Blue Book CCSDS 133.0-B-2
    """
    def __init__(
            self, packet_type: PacketTypes, apid: int, source_sequence_count: int, data_length: int,
            packet_version: int = 0b000, secondary_header_flag: bool = True,
            sequence_flags: SequenceFlags = SequenceFlags.UNSEGMENTED
    ):
        self.packet_type = packet_type
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
            packet_type=self.packet_type, secondary_header_flag=self.secondary_header_flag,
            apid=self.apid
        )

    @classmethod
    def __empty(cls) -> SpacePacketHeader:
        return SpacePacketHeader(
            packet_type=PacketTypes.PACKET_TYPE_TC,
            apid=0,
            source_sequence_count=0,
            data_length=0
        )

    def pack(self) -> bytearray:
        """Serialize raw space packet header.
        """
        header = bytearray()
        header.append((self.packet_id & 0xff00) >> 8)
        header.append(self.packet_id & 0xff)
        header.append((self.psc & 0xff00) >> 8)
        header.append(self.psc & 0xff)
        header.append((self.data_length & 0xff00) >> 8)
        header.append(self.data_length & 0xff)
        return header

    @classmethod
    def unpack(cls, space_packet_raw: bytes) -> SpacePacketHeader:
        """Unpack a raw space packet into the space packet header
        :raise ValueError: Raw packet length invalid"""
        if len(space_packet_raw) < SPACE_PACKET_HEADER_SIZE:
            logger = get_console_logger()
            logger.warning('Packet size smaller than PUS header size!')
            raise ValueError
        packet_type = space_packet_raw[0] & 0x10
        if packet_type == 0:
            packet_type = PacketTypes.PACKET_TYPE_TM
        else:
            packet_type = PacketTypes.PACKET_TYPE_TC
        packet_version = space_packet_raw[0] >> 5
        secondary_header_flag = (space_packet_raw[0] & 0x8) >> 3
        apid = ((space_packet_raw[0] & 0x7) << 8) | space_packet_raw[1]
        sequence_flags = (space_packet_raw[2] & 0xC0) >> 6
        ssc = ((space_packet_raw[2] << 8) | space_packet_raw[3]) & 0x3fff
        data_length = space_packet_raw[4] << 8 | space_packet_raw[5]
        return SpacePacketHeader(
            packet_type=packet_type,
            apid=apid,
            secondary_header_flag=bool(secondary_header_flag),
            packet_version=packet_version,
            data_length=data_length,
            sequence_flags=SequenceFlags(sequence_flags),
            source_sequence_count=ssc
        )

    def append_space_packet_header_content(self, content_list: list):
        content_list.append(str(hex(self.apid)))
        content_list.append(str(self.ssc))

    @staticmethod
    def append_space_packet_header_column_headers(header_list: list):
        header_list.append("APID")
        header_list.append("SSC")


def get_space_packet_id_bytes(
        packet_type: PacketTypes, secondary_header_flag: True, apid: int, version: int = 0b000
) -> Tuple[int, int]:
    """This function also includes the first three bits reserved for the version.

    :param version: Version field of the packet ID. Defined to be 0b000 in the space packet standard
    :param packet_type:
    :param secondary_header_flag: Indicates presence of absence of a Secondary Header
    in the Space Packet
    :param apid: Application Process Identifier. Naming mechanism for managed data path, has 11 bits
    :return:
    """
    byte_one = \
        ((version << 5) & 0xE0) | ((packet_type & 0x01) << 4) | \
        ((int(secondary_header_flag) & 0x01) << 3) | ((apid & 0x700) >> 8)
    byte_two = apid & 0xFF
    return byte_one, byte_two


def get_space_packet_id_num(
        packet_type: PacketTypes, secondary_header_flag: bool, apid: int
) -> int:
    """Get packet identification segment of packet primary header in integer format"""
    return (packet_type << 12 | int(secondary_header_flag) << 11 | apid) & 0x1fff


def get_space_packet_sequence_control(
        sequence_flags: SequenceFlags, source_sequence_count: int
) -> int:
    """Get sequence control in integer format
    """
    if sequence_flags > 3:
        logger = get_console_logger()
        logger.warning(
            "get_sp_packet_sequence_control: Sequence flag value larger than 0b11! "
            "Setting to 0b11.."
        )
        sequence_flags = SequenceFlags.UNSEGMENTED
    if source_sequence_count > 0x3fff:
        logger = get_console_logger()
        logger.warning(
            "get_sp_packet_sequence_control: Source sequence count largen than 0x3fff. "
            "Larger bits are cut off!"
        )
    return (source_sequence_count & 0x3FFF) | (sequence_flags << 14)


def get_space_packet_header(
        packet_id: int, packet_sequence_control: int, data_length: int
) -> bytearray:
    header = bytearray()
    header.append((packet_id & 0xff00) >> 8)
    header.append(packet_id & 0xff)
    header.append((packet_sequence_control & 0xff00) >> 8)
    header.append(packet_sequence_control & 0xff)
    header.append((data_length & 0xff00) >> 8)
    header.append(data_length & 0xff)
    return header


def get_space_packet_header_from_packet_id_bytes(
        packet_id_byte_one: int, packet_id_byte_two: int, packet_sequence_control: int,
        data_length: int
) -> bytearray:
    header = bytearray()
    header.append(packet_id_byte_one)
    header.append(packet_id_byte_two)
    header.append((packet_sequence_control & 0xFF00) >> 8)
    header.append(packet_sequence_control & 0xFF)
    header.append((data_length & 0xFF00) >> 8)
    header.append(data_length & 0xFF)
    return header


def get_apid_from_raw_space_packet(raw_packet: bytes) -> int:
    if len(raw_packet) < 6:
        return 0
    return ((raw_packet[0] & 0x7) << 8) | raw_packet[1]


def get_total_space_packet_len_from_len_field(len_field: int):
    """Definition of length field is: C = (Octets in data field - 1).
    Therefore, octets in data field in len_field plus one. The total space packet length
    is therefore len_field plus one plus the space packet header size (6)"""
    return len_field + SPACE_PACKET_HEADER_SIZE + 1


def parse_space_packets(
        analysis_queue: Deque[bytearray], packet_id: int, max_len: int
) -> List[bytearray]:
    """Given a deque of bytearrays, parse for space packets. Any broken headers will be removed.
    Any broken tail packets will be reinserted into the given deque
    :param analysis_queue:
    :param packet_id:
    :param max_len:     Maximum allowed packet length
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
        if current_idx > max_len - 6 or current_idx > len(concatenated_packets) - 1:
            break
        try:
            current_packet_id = \
                (concatenated_packets[current_idx] << 8) | concatenated_packets[current_idx + 1]
        except IndexError:
            logger = get_console_logger()
            logger.warning(
                f'Index error, current index {current_idx} larger than length of concatenated '
                f'packets {len(concatenated_packets)}'
            )
            return tm_list
        if current_packet_id == packet_id:
            result, current_idx = __handle_packet_id_match(
                concatenated_packets=concatenated_packets, analysis_queue=analysis_queue,
                max_len=max_len, current_idx=current_idx, tm_list=tm_list
            )
            if result != 0:
                break
        else:
            # Keep parsing until a packet ID is found
            current_idx += 1
    return tm_list


def __handle_packet_id_match(
        concatenated_packets: bytearray, analysis_queue: Deque[bytearray], max_len: int,
        current_idx: int, tm_list: List[bytearray]
) -> (int, int):
    next_packet_len_field = \
        concatenated_packets[current_idx + 4] | concatenated_packets[current_idx + 5]
    total_packet_len = get_total_space_packet_len_from_len_field(next_packet_len_field)
    if total_packet_len > max_len:
        print(
            f'parse_space_packets: Detected packet length larger than specified maximum'
            f'length {max_len}. Skipping header..'
        )
        # Packet too long. Throw away the header and advance index
        current_idx += 6
    # Might be part of packet. Put back into analysis queue as whole
    elif total_packet_len > len(concatenated_packets):
        analysis_queue.appendleft(concatenated_packets)
        return -1, current_idx
    else:
        tm_list.append(
            concatenated_packets[current_idx: current_idx + total_packet_len]
        )
        current_idx += total_packet_len
    return 0, current_idx
