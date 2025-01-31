"""This module also includes the :py:class:`SpacePacketHeader` class, which is the header component
of all CCSDS packets."""

from __future__ import annotations

import enum
import struct
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Final

from spacepackets.exceptions import BytesTooShortError

if TYPE_CHECKING:
    from collections import deque
    from collections.abc import Sequence

CCSDS_HEADER_LEN: Final[int] = 6
SPACE_PACKET_HEADER_SIZE: Final[int] = CCSDS_HEADER_LEN
SEQ_FLAG_MASK: Final[int] = 0xC000
APID_MASK: Final[int] = 0x7FF
PACKET_ID_MASK: Final[int] = 0x1FFF
MAX_SEQ_COUNT: Final[int] = pow(2, 14) - 1
MAX_APID: Final[int] = pow(2, 11) - 1


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
        if seq_count > MAX_SEQ_COUNT or seq_count < 0:
            raise ValueError(f"Sequence count larger than allowed {pow(2, 14) - 1} or negative")
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
    def empty(cls) -> PacketSeqCtrl:
        return cls(seq_flags=SequenceFlags.CONTINUATION_SEGMENT, seq_count=0)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, PacketSeqCtrl):
            return self.raw() == other.raw()
        return False

    @classmethod
    def from_raw(cls, raw: int) -> PacketSeqCtrl:
        return cls(seq_flags=SequenceFlags((raw >> 14) & 0b11), seq_count=raw & ~SEQ_FLAG_MASK)


class PacketId:
    """The packet ID forms the last thirteen bits of the first two bytes of the
    space packet header."""

    def __init__(self, ptype: PacketType, sec_header_flag: bool, apid: int):
        if apid > pow(2, 11) - 1 or apid < 0:
            raise ValueError(f"Invalid APID, exceeds maximum value {pow(2, 11) - 1} or negative")
        self.ptype = ptype
        self.sec_header_flag = sec_header_flag
        self.apid = apid

    @classmethod
    def empty(cls) -> PacketId:
        return cls(ptype=PacketType.TM, sec_header_flag=False, apid=0)

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(ptype={self.ptype!r}, "
            f"sec_header_flag={self.sec_header_flag!r}, apid={self.apid!r})"
        )

    def __str__(self):
        pstr = "TM" if self.ptype == PacketType.TM else "TC"
        return (
            f"Packet ID: [Packet Type: {pstr}, Sec Header Flag: {self.sec_header_flag},"
            f" APID: {self.apid:#05x}]"
        )

    def raw(self) -> int:
        return self.ptype << 12 | self.sec_header_flag << 11 | self.apid

    def __eq__(self, other: object) -> bool:
        if isinstance(other, PacketId):
            return self.raw() == other.raw()
        return False

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
    def ccsds_version(self) -> int:
        pass

    @property
    @abstractmethod
    def packet_id(self) -> PacketId:
        pass

    @property
    @abstractmethod
    def packet_seq_control(self) -> PacketSeqCtrl:
        pass

    @property
    def packet_type(self) -> PacketType:
        return self.packet_id.ptype

    @property
    def apid(self) -> int:
        return self.packet_id.apid

    @property
    def sec_header_flag(self) -> bool:
        return self.packet_id.sec_header_flag

    @property
    def seq_count(self) -> int:
        return self.packet_seq_control.seq_count

    @property
    def seq_flags(self) -> SequenceFlags:
        return self.packet_seq_control.seq_flags

    @abstractmethod
    def pack(self) -> bytearray:
        pass


class SpacePacketHeader(AbstractSpacePacket):
    """This class encapsulates the space packet header. Packet reference: Blue Book
    CCSDS 133.0-B-2"""

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

        The data length field can also be set from the total packet length by using the
        :py:meth:`set_data_len_from_packet_len` method after construction of the space packet
        header object.

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
        >>> sph.packet_seq_control
        PacketSeqCtrl(seq_flags=<SequenceFlags.UNSEGMENTED: 3>, seq_count=0)

        Parameters
        -----------
        packet_type: PacketType
            0 for Telemetery, 1 for Telecommands
        apid: int
            Application Process ID, should not be larger than 11 bits, deciaml 2074 or hex 0x7ff
        seq_count: int
            Source sequence counter, should not be larger than 0x3fff or decimal 16383
        data_len: int
            Contains a length count C that equals one fewer than the length of the packet data
            field. Should not be larger than 65535 bytes
        sec_header_flag: bool
            Secondary header flag, or False by default.
        seq_flags:
            Sequence flags, defaults to unsegmented.
        ccsds_version: int
            Version of the CCSDS packet. Defaults to 0b000

        Raises
        --------
        ValueError
            On invalid parameters
        """
        if data_len > pow(2, 16) - 1 or data_len < 0:
            raise ValueError(
                "Invalid data length value, exceeds maximum value of"
                f" {pow(2, 16) - 1} or negative"
            )
        self._ccsds_version = ccsds_version
        self._packet_id = PacketId(ptype=packet_type, sec_header_flag=sec_header_flag, apid=apid)
        self._psc = PacketSeqCtrl(seq_flags=seq_flags, seq_count=seq_count)
        self.data_len = data_len

    @classmethod
    def tc(
        cls,
        apid: int,
        seq_count: int,
        data_len: int,
        sec_header_flag: bool = False,
        seq_flags: SequenceFlags = SequenceFlags.UNSEGMENTED,
        ccsds_version: int = 0b000,
    ) -> SpacePacketHeader:
        """Create a space packet header with the given field parameters for a telecommand packet.
        Calls the default constructor :py:meth:`SpacePacketHeader` with the packet type
        set to :py:class:`PacketType.TC`.
        """
        return cls(
            packet_type=PacketType.TC,
            apid=apid,
            seq_count=seq_count,
            data_len=data_len,
            sec_header_flag=sec_header_flag,
            seq_flags=seq_flags,
            ccsds_version=ccsds_version,
        )

    @classmethod
    def tm(
        cls,
        apid: int,
        seq_count: int,
        data_len: int,
        sec_header_flag: bool = False,
        seq_flags: SequenceFlags = SequenceFlags.UNSEGMENTED,
        ccsds_version: int = 0b000,
    ) -> SpacePacketHeader:
        """Create a space packet header with the given field parameters for a telemetry packet.
        Calls the default constructor :py:meth:`SpacePacketHeader` with the packet type
        set to :py:class:`PacketType.TM`.
        """
        return cls(
            packet_type=PacketType.TM,
            apid=apid,
            seq_count=seq_count,
            data_len=data_len,
            sec_header_flag=sec_header_flag,
            seq_flags=seq_flags,
            ccsds_version=ccsds_version,
        )

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
        header.extend(struct.pack("!H", self._psc.raw()))
        header.extend(struct.pack("!H", self.data_len))
        return header

    @property
    def ccsds_version(self) -> int:
        return self._ccsds_version

    @property
    def packet_id(self) -> PacketId:
        return self._packet_id

    @property
    def packet_type(self) -> PacketType:
        return self.packet_id.ptype

    @packet_type.setter
    def packet_type(self, packet_type: PacketType) -> None:
        self.packet_id.ptype = packet_type

    @property
    def apid(self) -> int:
        return self._packet_id.apid

    @property
    def packet_seq_control(self) -> PacketSeqCtrl:
        return self._psc

    @property
    def sec_header_flag(self) -> bool:
        return self._packet_id.sec_header_flag

    @sec_header_flag.setter
    def sec_header_flag(self, value: bool) -> None:
        self._packet_id.sec_header_flag = value

    @property
    def seq_count(self) -> int:
        return self._psc.seq_count

    def set_data_len_from_packet_len(self, packet_len: int) -> None:
        """Sets the data length field from the given total packet length. The total packet length
        must be at least 7 bytes.

        Raises
        -------
        ValueError
            The passed packet length is smaller than the minimum expected 7 bytes.
        """
        if packet_len < CCSDS_HEADER_LEN + 1:
            raise ValueError("specified total packet length too short")
        self.data_len = packet_len - CCSDS_HEADER_LEN - 1

    @seq_count.setter
    def seq_count(self, seq_cnt: int) -> None:
        self._psc.seq_count = seq_cnt

    @property
    def seq_flags(self) -> SequenceFlags:
        return self._psc.seq_flags

    @seq_flags.setter
    def seq_flags(self, value: SequenceFlags) -> None:
        self._psc.seq_flags = value

    @property
    def header_len(self) -> int:
        return CCSDS_HEADER_LEN

    @apid.setter
    def apid(self, apid: int) -> None:
        self.packet_id.apid = apid

    @property
    def packet_len(self) -> int:
        """Retrieve the full space packet size when packed.

        The full packet size is the data length field plus the :py:const:`CCSDS_HEADER_LEN` of 6
        bytes plus one.

        Returns
        --------
        Size of the TM packet based on the space packet header data length field.
        """
        return CCSDS_HEADER_LEN + self.data_len + 1

    @classmethod
    def unpack(cls, data: bytes | bytearray) -> SpacePacketHeader:
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
            f"{self.__class__.__name__}(packet_version={self.ccsds_version!r},"
            f" packet_type={self.packet_type!r}, apid={self.apid!r},"
            f" seq_cnt={self.seq_count!r}, data_len={self.data_len!r},"
            f" sec_header_flag={self.sec_header_flag!r}, seq_flags={self.seq_flags!r})"
        )

    def __eq__(self, other: object):
        if isinstance(other, SpacePacketHeader):
            return self.pack() == other.pack()
        return False


SpHeader = SpacePacketHeader


class SpacePacket:
    """Generic CCSDS space packet which consists of the primary header and can optionally include
    a secondary header and a user data field.

    If the secondary header flag in the primary header is set, the secondary header in mandatory.
    If it is not set, the user data is mandatory."""

    def __init__(
        self,
        sp_header: SpacePacketHeader,
        sec_header: bytes | bytearray | None,
        user_data: bytes | bytearray | None,
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
        """Pack the raw byte representation of the space packet.

        Raises
        --------
        ValueError
            Mandatory fields were not supplied properly"""
        packet = self.sp_header.pack()
        if self.sp_header.sec_header_flag:
            if self.sec_header is None:
                raise ValueError(
                    "Secondary header flag is set but no secondary header was supplied"
                )
            packet.extend(self.sec_header)
        elif self.user_data is None:
            raise ValueError("Secondary header not present but no user data supplied")
        if self.user_data is not None:
            packet.extend(self.user_data)
        return packet

    @property
    def apid(self) -> int:
        return self.sp_header.apid

    @property
    def seq_count(self) -> int:
        return self.sp_header.seq_count

    @property
    def sec_header_flag(self) -> bool:
        return self.sp_header.sec_header_flag

    def __eq__(self, other: object):
        if isinstance(other, SpacePacket):
            return (
                self.sp_header == other.sp_header
                and self.sec_header == other.sec_header
                and self.user_data == other.user_data
            )
        return False


def get_space_packet_id_bytes(
    packet_type: PacketType,
    secondary_header_flag: bool,
    apid: int,
    version: int = 0b000,
) -> tuple[int, int]:
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


def get_sp_packet_id_raw(packet_type: PacketType, secondary_header_flag: bool, apid: int) -> int:
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


def get_total_space_packet_len_from_len_field(len_field: int) -> int:
    """Definition of length field is: C = (Octets in data field - 1).
    Therefore, octets in data field in len_field plus one. The total space packet length
    is therefore len_field plus one plus the space packet header size (6)"""
    return len_field + SPACE_PACKET_HEADER_SIZE + 1


def parse_space_packets(
    analysis_queue: deque[bytearray], packet_ids: Sequence[PacketId]
) -> list[bytearray]:
    """This calls :py:func:`parse_space_packets_with_skipped_bytes` and returns only the parsed
    packets."""
    return parse_space_packets_with_skipped_bytes_report(analysis_queue, packet_ids)[0]


def parse_space_packets_with_skipped_bytes_report(
    analysis_queue: deque[bytearray], packet_ids: Sequence[PacketId]
) -> tuple[list[bytearray], int]:
    """Given a deque of bytearrays, parse for space packets. This funtion expects the deque
    to be filled on the right side, for example with :py:meth:`collections.deque.append`.
    If a split packet with a valid header is detected, this function will re-insert the header into
    the given deque on the right side.

    :param analysis_queue:
    :param packet_ids:
    :return: Tuple where the first entry is the list of parse packets and the second entry is the
    number of skipped bytes. Bytes are skipped if the first two bytes in the data stream do not
    match the packet ID.
    """
    ids_raw = [packet_id.raw() for packet_id in packet_ids]
    skipped_bytes = 0
    tm_list = []
    concatenated_packets = bytearray()
    if not analysis_queue:
        return (tm_list, skipped_bytes)
    while analysis_queue:
        # Put it all in one buffer
        concatenated_packets.extend(analysis_queue.popleft())
    current_idx = 0
    if len(concatenated_packets) < 6:
        return (tm_list, skipped_bytes)
    # Packet ID detected
    while True:
        # Can't even parse CCSDS header. Wait for more data to arrive.
        if current_idx + CCSDS_HEADER_LEN >= len(concatenated_packets):
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
            skipped_bytes += 1
    return (tm_list, skipped_bytes)


def __handle_packet_id_match(
    concatenated_packets: bytearray,
    analysis_queue: deque[bytearray],
    current_idx: int,
    tm_list: list[bytearray],
) -> tuple[int, int]:
    total_packet_len = get_total_space_packet_len_from_len_field(
        struct.unpack("!H", concatenated_packets[current_idx + 4 : current_idx + 6])[0]
    )
    # Might be part of packet. Put back into analysis queue as whole
    if current_idx + total_packet_len > len(concatenated_packets):
        # Clear the queue first. We are done with parsing
        analysis_queue.clear()
        analysis_queue.append(concatenated_packets[current_idx:])
        return -1, current_idx
    tm_list.append(concatenated_packets[current_idx : current_idx + total_packet_len])
    current_idx += total_packet_len
    return 0, current_idx
