"""This module contains the PUS telecommand class representation to pack telecommands, most notably
the :py:class:`PusTelecommand` class.
"""
from __future__ import annotations

from spacepackets import __version__, BytesTooShortError
import struct
from typing import Tuple, Optional

import deprecation
from spacepackets.ecss.crc import CRC16_CCITT_FUNC
from crcmod.predefined import PredefinedCrc

from spacepackets.ccsds.spacepacket import (
    SpacePacketHeader,
    PacketType,
    SPACE_PACKET_HEADER_SIZE,
    SpacePacket,
    PacketId,
    PacketSeqCtrl,
    SequenceFlags,
)
from spacepackets.ecss.conf import (
    get_default_tc_apid,
    PusVersion,
    FETCH_GLOBAL_APID,
)


class PusTcDataFieldHeader:
    PUS_C_SEC_HEADER_LEN = 5

    def __init__(
        self,
        service: int,
        subservice: int,
        source_id: int = 0,
        ack_flags: int = 0b1111,
    ):
        """Create a PUS TC data field header instance

        :param service:
        :param subservice:
        :param source_id:
        :param ack_flags:
        """
        self.service = service
        self.subservice = subservice
        self.source_id = source_id
        self.pus_version = PusVersion.PUS_C
        self.ack_flags = ack_flags

    def pack(self) -> bytearray:
        header_raw = bytearray()
        header_raw.append(self.pus_version << 4 | self.ack_flags)
        header_raw.append(self.service)
        header_raw.append(self.subservice)
        header_raw.extend(struct.pack("!H", self.source_id))
        return header_raw

    @classmethod
    def unpack(cls, data: bytes) -> PusTcDataFieldHeader:
        """Unpack a TC data field header.

        :param data: Start of raw data belonging to the TC data field header
        :raises BytesTooShortError: Passed data too short.
        :return:
        """
        min_expected_len = cls.get_header_size()
        if len(data) < min_expected_len:
            raise BytesTooShortError(min_expected_len, len(data))
        version_and_ack_byte = data[0]
        pus_version = (version_and_ack_byte & 0xF0) >> 4
        if pus_version != PusVersion.PUS_C:
            raise ValueError("This implementation only supports PUS C")
        ack_flags = version_and_ack_byte & 0x0F
        service = data[1]
        subservice = data[2]
        source_id = struct.unpack("!H", data[3:5])[0]
        return cls(
            service=service,
            subservice=subservice,
            ack_flags=ack_flags,
            source_id=source_id,
        )

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(service={self.service!r}, subservice={self.subservice!r},"
            f" ack_flags={self.ack_flags!r} "
        )

    def __eq__(self, other: PusTcDataFieldHeader):
        return self.pack() == other.pack()

    @classmethod
    def get_header_size(cls):
        return cls.PUS_C_SEC_HEADER_LEN


class InvalidTcCrc16(Exception):
    def __init__(self, tc: PusTelecommand):
        self.tc = tc


class PusTelecommand:
    """Class representation of a PUS telecommand. Can be converted to the raw byte representation
    but also unpacked from a raw byte stream. Only PUS C telecommands are supported.

    >>> ping_tc = PusTelecommand(service=17, subservice=1, seq_count=22, apid=0x01)
    >>> ping_tc.service
    17
    >>> ping_tc.subservice
    1
    >>> ping_tc.pack().hex(sep=',')
    '18,01,c0,16,00,06,2f,11,01,00,00,ab,62'

    """

    def __init__(
        self,
        service: int,
        subservice: int,
        app_data: bytes = bytes([]),
        apid: int = FETCH_GLOBAL_APID,
        seq_count: int = 0,
        source_id: int = 0,
        ack_flags: int = 0b1111,
    ):
        """Initiate a PUS telecommand from the given parameters. The raw byte representation
        can then be retrieved with the :py:meth:`pack` function.

        :param service: PUS service number
        :param subservice: PUS subservice number
        :param apid: Application Process ID as specified by CCSDS
        :param seq_count: Source Sequence Count. Application should take care of incrementing this.
            Limited to 2 to the power of 14 by the number of bits in the header
        :param app_data: Application data in the Packet Data Field
        :param source_id: Source ID will be supplied as well. Can be used to distinguish
            different packet sources (e.g. different ground stations)
        :raises ValueError: Invalid input parameters
        """
        if apid == FETCH_GLOBAL_APID:
            apid = get_default_tc_apid()
        self.pus_tc_sec_header = PusTcDataFieldHeader(
            service=service,
            subservice=subservice,
            ack_flags=ack_flags,
            source_id=source_id,
        )
        data_length = self.get_data_length(
            secondary_header_len=self.pus_tc_sec_header.get_header_size(),
            app_data_len=len(app_data),
        )
        self.sp_header = SpacePacketHeader(
            apid=apid,
            sec_header_flag=True,
            packet_type=PacketType.TC,
            seq_flags=SequenceFlags.UNSEGMENTED,
            data_len=data_length,
            seq_count=seq_count,
        )
        self._app_data = app_data
        self._valid = True
        self._crc16: Optional[bytes] = None

    @classmethod
    def from_sp_header(
        cls,
        sp_header: SpacePacketHeader,
        service: int,
        subservice: int,
        app_data: bytes = bytes([]),
        source_id: int = 0,
        ack_flags: int = 0b1111,
    ):
        pus_tc = cls.empty()
        sp_header.packet_type = PacketType.TC
        sp_header.sec_header_flag = True
        sp_header.data_len = PusTelecommand.get_data_length(
            secondary_header_len=PusTcDataFieldHeader.get_header_size(),
            app_data_len=len(app_data),
        )
        pus_tc.sp_header = sp_header
        pus_tc.pus_tc_sec_header = PusTcDataFieldHeader(
            service=service,
            subservice=subservice,
            source_id=source_id,
            ack_flags=ack_flags,
        )
        pus_tc._app_data = app_data
        return pus_tc

    @classmethod
    def from_composite_fields(
        cls,
        sp_header: SpacePacketHeader,
        sec_header: PusTcDataFieldHeader,
        app_data: bytes = bytes([]),
    ) -> PusTelecommand:
        pus_tc = cls.empty()
        if sp_header.packet_type == PacketType.TM:
            raise ValueError(
                f"Invalid Packet Type {sp_header.packet_type} in CCSDS primary header"
            )
        pus_tc.sp_header = sp_header
        pus_tc.pus_tc_sec_header = sec_header
        pus_tc._app_data = app_data
        return pus_tc

    @classmethod
    def empty(cls) -> PusTelecommand:
        return PusTelecommand(service=0, subservice=0)

    def __repr__(self):
        """Returns the representation of a class instance."""
        return (
            f"{self.__class__.__name__}.from_composite_fields(sp_header={self.sp_header!r}, "
            f"sec_header={self.pus_tc_sec_header!r}, app_data={self.app_data!r})"
        )

    def __str__(self):
        """Returns string representation of a class instance."""
        from .req_id import RequestId

        return (
            f"PUS TC[{self.pus_tc_sec_header.service}, {self.pus_tc_sec_header.subservice}] with "
            f"Request ID {RequestId.from_sp_header(self.sp_header).as_u32():#08x}"
            f", APID {self.apid:#05x}, SSC {self.sp_header.seq_count}"
        )

    def __eq__(self, other: PusTelecommand):
        return (
            self.sp_header == other.sp_header
            and self.pus_tc_sec_header == other.pus_tc_sec_header
            and self._app_data == other._app_data
        )

    def to_space_packet(self) -> SpacePacket:
        """Retrieve the generic CCSDS space packet representation. This also calculates the CRC16
        before converting the PUS TC to a generic Space Packet"""
        self.calc_crc()
        user_data = bytearray(self._app_data)
        user_data.extend(self._crc16)
        return SpacePacket(self.sp_header, self.pus_tc_sec_header.pack(), user_data)

    def calc_crc(self):
        """Can be called to calculate the CRC16. Also sets the internal CRC16 field."""
        crc = PredefinedCrc(crc_name="crc-ccitt-false")
        crc.update(self.sp_header.pack())
        crc.update(self.pus_tc_sec_header.pack())
        crc.update(self.app_data)
        self._crc16 = struct.pack("!H", crc.crcValue)

    def pack(self, recalc_crc: bool = True) -> bytearray:
        """Serializes the TC data fields into a bytearray.

        :param recalc_crc: Can be set to False if the CRC was previous calculated and no fields were
            changed. This is set to True by default to ensure the CRC is always valid by default,
            even if the user changes arbitrary fields after TC creation.
        """
        packed_data = bytearray()
        packed_data.extend(self.sp_header.pack())
        packed_data.extend(self.pus_tc_sec_header.pack())
        packed_data += self.app_data
        if self._crc16 is None or recalc_crc:
            self._crc16 = struct.pack("!H", CRC16_CCITT_FUNC(packed_data))
        packed_data.extend(self._crc16)
        return packed_data

    @classmethod
    def unpack(cls, data: bytes) -> PusTelecommand:
        """Create an instance from a raw bytestream.

        :raises BytesTooShortError: Passed bytestream too short.
        :raises ValueError: Unsupported PUS version.
        :raises InvalidTcCrc16: Invalid CRC16.
        """
        tc_unpacked = cls.empty()
        tc_unpacked.sp_header = SpacePacketHeader.unpack(data=data)
        tc_unpacked.pus_tc_sec_header = PusTcDataFieldHeader.unpack(
            data=data[SPACE_PACKET_HEADER_SIZE:]
        )
        header_len = (
            SPACE_PACKET_HEADER_SIZE + tc_unpacked.pus_tc_sec_header.get_header_size()
        )
        expected_packet_len = tc_unpacked.packet_len
        if len(data) < expected_packet_len:
            raise BytesTooShortError(expected_packet_len, len(data))
        tc_unpacked._app_data = data[header_len : expected_packet_len - 2]
        tc_unpacked._crc16 = data[expected_packet_len - 2 : expected_packet_len]
        if CRC16_CCITT_FUNC(data[:expected_packet_len]) != 0:
            raise InvalidTcCrc16(tc_unpacked)
        return tc_unpacked

    @property
    def packet_len(self) -> int:
        """Retrieve the full packet size when packed
        :return: Size of the TM packet based on the space packet header data length field.
        The space packet data field is the full length of data field minus one without
        the space packet header.
        """
        return self.sp_header.packet_len

    @staticmethod
    def get_data_length(app_data_len: int, secondary_header_len: int) -> int:
        """Retrieve size of TC packet in bytes.
        Formula according to PUS Standard: C = (Number of octets in packet data field) - 1.
        The size of the TC packet is the size of the packet secondary header with
        source ID + the length of the application data + length of the CRC16 checksum - 1
        """
        data_length = secondary_header_len + app_data_len + 1
        return data_length

    @deprecation.deprecated(
        deprecated_in="v0.14.0rc3",
        current_version=__version__,
        details="use pack and the class itself to build this instead",
    )
    def pack_command_tuple(self) -> Tuple[bytearray, PusTelecommand]:
        """Pack a tuple consisting of the raw packet as the first entry and the class representation
        as the second entry
        """
        command_tuple = (self.pack(), self)
        return command_tuple

    @property
    def service(self) -> int:
        return self.pus_tc_sec_header.service

    @property
    def subservice(self) -> int:
        return self.pus_tc_sec_header.subservice

    @property
    def source_id(self) -> int:
        return self.pus_tc_sec_header.source_id

    @source_id.setter
    def source_id(self, source_id: int):
        self.pus_tc_sec_header.source_id = source_id

    @property
    def seq_count(self) -> int:
        return self.sp_header.seq_count

    @property
    def apid(self) -> int:
        return self.sp_header.apid

    @property
    def packet_id(self) -> PacketId:
        return self.sp_header.packet_id

    @property
    def packet_seq_ctrl(self) -> PacketSeqCtrl:
        return self.sp_header.psc

    @property
    def app_data(self) -> bytes:
        return self._app_data

    @property
    def crc16(self) -> Optional[bytes]:
        """Will be the raw CRC16 if the telecommand was created using :py:meth:`unpack`,
        :py:meth:`pack` was called at least once or :py:meth:`calc_crc` was called at
        least once."""
        return self._crc16

    @seq_count.setter
    def seq_count(self, value):
        self.sp_header.seq_count = value

    @apid.setter
    def apid(self, apid):
        self.sp_header.apid = apid


def generate_packet_crc(tc_packet: bytearray) -> bytes:
    """Removes current Packet Error Control, calculates new
    CRC16 checksum and adds it as correct Packet Error Control Code.
    Reference: ECSS-E70-41A p. 207-212
    """
    crc = CRC16_CCITT_FUNC(tc_packet[0 : len(tc_packet) - 2])
    tc_packet[len(tc_packet) - 2] = (crc & 0xFF00) >> 8
    tc_packet[len(tc_packet) - 1] = crc & 0xFF
    return tc_packet


def generate_crc(data: bytearray) -> bytes:
    """Takes the application data, appends the CRC16 checksum and returns resulting bytearray"""
    data_with_crc = bytearray()
    data_with_crc += data
    crc = CRC16_CCITT_FUNC(data)
    data_with_crc.extend(struct.pack("!H", crc))
    return data_with_crc
