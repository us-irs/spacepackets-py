"""This module contains the PUS telecommand class representation to pack telecommands, most notably
the :py:class:`PusTelecommand` class.
"""

from __future__ import annotations

import struct

import deprecation
from fastcrc import crc16

from spacepackets import BytesTooShortError
from spacepackets.ccsds.spacepacket import (
    CCSDS_HEADER_LEN,
    AbstractSpacePacket,
    PacketId,
    PacketSeqCtrl,
    PacketType,
    SequenceFlags,
    SpacePacket,
    SpacePacketHeader,
)
from spacepackets.ecss.defs import PusVersion
from spacepackets.ecss.req_id import RequestId
from spacepackets.version import get_version


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
    def unpack(cls, data: bytes | bytearray) -> PusTcDataFieldHeader:
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
            f"{self.__class__.__name__}(service={self.service!r},"
            f" subservice={self.subservice!r}, ack_flags={self.ack_flags!r} "
        )

    def __hash__(self):
        return hash(
            (self.pus_version, self.service, self.subservice, self.source_id, self.ack_flags)
        )

    def __eq__(self, other: object):
        if isinstance(other, PusTcDataFieldHeader):
            return (
                other.pus_version == self.pus_version
                and self.service == other.service
                and self.subservice == other.subservice
                and self.source_id == other.source_id
                and self.ack_flags == other.ack_flags
            )
        return False

    @classmethod
    def get_header_size(cls) -> int:
        return cls.PUS_C_SEC_HEADER_LEN


class InvalidTcCrc16Error(Exception):
    def __init__(self, tc: PusTc | None):
        self.tc = tc


class PusTc(AbstractSpacePacket):
    """Class representation of a PUS telecommand. Can be converted to the raw byte representation
    but also unpacked from a raw byte stream. Only PUS C telecommands are supported.

    >>> ping_tc = PusTc(service=17, subservice=1, seq_count=22, apid=0x01)
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
        has_checksum: bool = True,
        apid: int = 0,
        app_data: bytes | bytearray = b"",
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
        self.pus_tc_sec_header = PusTcDataFieldHeader(
            service=service,
            subservice=subservice,
            ack_flags=ack_flags,
            source_id=source_id,
        )
        data_length = self.get_data_length(
            secondary_header_len=self.pus_tc_sec_header.get_header_size(),
            app_data_len=len(app_data),
            has_checksum=has_checksum,
        )
        self.sp_header = SpacePacketHeader(
            apid=apid,
            sec_header_flag=True,
            packet_type=PacketType.TC,
            seq_flags=SequenceFlags.UNSEGMENTED,
            data_len=data_length,
            seq_count=seq_count,
        )
        self._has_checksum = has_checksum
        self._app_data = app_data
        self._valid = True
        self._crc16: bytes | None = None

    @classmethod
    def from_sp_header(
        cls,
        sp_header: SpacePacketHeader,
        service: int,
        subservice: int,
        app_data: bytes = bytes([]),
        source_id: int = 0,
        ack_flags: int = 0b1111,
        has_checksum: bool = True,
    ) -> PusTc:
        pus_tc = cls.empty()
        sp_header.packet_type = PacketType.TC
        sp_header.sec_header_flag = True
        sp_header.data_len = PusTc.get_data_length(
            secondary_header_len=PusTcDataFieldHeader.get_header_size(),
            app_data_len=len(app_data),
            has_checksum=has_checksum,
        )
        pus_tc.sp_header = sp_header
        pus_tc.pus_tc_sec_header = PusTcDataFieldHeader(
            service=service,
            subservice=subservice,
            source_id=source_id,
            ack_flags=ack_flags,
        )
        pus_tc._app_data = app_data
        pus_tc._has_checksum = has_checksum
        return pus_tc

    @classmethod
    def from_composite_fields(
        cls,
        sp_header: SpacePacketHeader,
        sec_header: PusTcDataFieldHeader,
        app_data: bytes = bytes([]),
        has_checksum: bool = True,
    ) -> PusTc:
        pus_tc = cls.empty()
        if sp_header.packet_type == PacketType.TM:
            raise ValueError(f"Invalid Packet Type {sp_header.packet_type} in CCSDS primary header")
        pus_tc.sp_header = sp_header
        pus_tc.pus_tc_sec_header = sec_header
        pus_tc._app_data = app_data
        pus_tc._has_checksum = has_checksum
        sp_header.data_len = PusTc.get_data_length(
            secondary_header_len=sec_header.get_header_size(),
            app_data_len=len(app_data),
            has_checksum=has_checksum,
        )
        return pus_tc

    @classmethod
    def empty(cls) -> PusTc:
        return PusTc(apid=0, service=0, subservice=0)

    def __repr__(self):
        """Returns the representation of a class instance."""
        return (
            f"{self.__class__.__name__}.from_composite_fields(sp_header={self.sp_header!r},"
            f" sec_header={self.pus_tc_sec_header!r}, app_data={self.app_data!r})"
        )

    def __str__(self):
        """Returns string representation of a class instance."""

        return (
            f"PUS TC[{self.pus_tc_sec_header.service},"
            f" {self.pus_tc_sec_header.subservice}] with Request ID"
            f" {RequestId.from_sp_header(self.sp_header).as_u32():#08x}, APID"
            f" {self.apid:#05x}, SSC {self.sp_header.seq_count}"
        )

    def __eq__(self, other: object):
        if isinstance(other, PusTc):
            return (
                self.sp_header == other.sp_header
                and self.pus_tc_sec_header == other.pus_tc_sec_header
                and self._app_data == other._app_data
            )
        return False

    def __hash__(self):
        return hash(
            (
                self.sp_header,
                self.pus_tc_sec_header,
                self._app_data,
            )
        )

    def to_space_packet(self) -> SpacePacket:
        """Retrieve the generic CCSDS space packet representation. This also calculates the CRC16
        before converting the PUS TC to a generic Space Packet"""
        user_data = bytearray(self._app_data)
        if self._has_checksum:
            self.calc_crc()
            user_data.extend(self._crc16)  # type: ignore
        return SpacePacket(self.sp_header, self.pus_tc_sec_header.pack(), user_data)

    def calc_crc(self) -> None:
        """Can be called to calculate the CRC16. Also sets the internal CRC16 field."""
        crc_calc = crc16.ibm_3740(bytes(self.sp_header.pack()))
        crc_calc = crc16.ibm_3740(bytes(self.pus_tc_sec_header.pack()), crc_calc)
        crc_calc = crc16.ibm_3740(self.app_data, crc_calc)
        self._crc16 = struct.pack("!H", crc_calc)

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
        if self._has_checksum:
            if self._crc16 is None or recalc_crc:
                self._crc16 = struct.pack("!H", crc16.ibm_3740(bytes(packed_data)))
            packed_data.extend(self._crc16)
        return packed_data

    @classmethod
    def unpack(cls, data: bytes | bytearray) -> PusTc:
        """Create an instance from a raw bytestream, expecting a checksum and verifying it as well.

        :raises BytesTooShortError: Passed bytestream too short.
        :raises ValueError: Unsupported PUS version.
        :raises InvalidTcCrc16Error: Invalid CRC16 checksum.
        """
        return cls.unpack_generic(data, verify_checksum=True, has_checksum=True)

    @classmethod
    def unpack_no_checksum(cls, data: bytes | bytearray) -> PusTc:
        """Create an instance from a raw bytestream with no checksum.

        :raises BytesTooShortError: Passed bytestream too short.
        :raises ValueError: Unsupported PUS version.
        :raises InvalidTcCrc16Error: Invalid CRC16.
        """
        return cls.unpack_generic(data, has_checksum=False, verify_checksum=False)

    @classmethod
    def unpack_generic(
        cls, data: bytes | bytearray, has_checksum: bool, verify_checksum: bool
    ) -> PusTc:
        """Create an instance from a raw bytestream.

        :raises BytesTooShortError: Passed bytestream too short.
        :raises ValueError: Unsupported PUS version.
        :raises InvalidTcCrc16Error: Invalid CRC16.
        """
        tc_unpacked = cls.empty()
        tc_unpacked.sp_header = SpacePacketHeader.unpack(data=data)
        tc_unpacked.pus_tc_sec_header = PusTcDataFieldHeader.unpack(data=data[CCSDS_HEADER_LEN:])
        header_len = CCSDS_HEADER_LEN + tc_unpacked.pus_tc_sec_header.get_header_size()
        expected_packet_len = tc_unpacked.packet_len
        if len(data) < expected_packet_len:
            raise BytesTooShortError(expected_packet_len, len(data))
        if not has_checksum:
            tc_unpacked._app_data = data[header_len:expected_packet_len]
        else:
            tc_unpacked._app_data = data[header_len : expected_packet_len - 2]
            if verify_checksum:
                tc_unpacked._crc16 = bytes(data[expected_packet_len - 2 : expected_packet_len])
                if verify_checksum and crc16.ibm_3740(bytes(data[:expected_packet_len])) != 0:
                    raise InvalidTcCrc16Error(tc_unpacked)
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
    def get_data_length(app_data_len: int, secondary_header_len: int, has_checksum: bool) -> int:
        """Retrieve size of TC packet in bytes.
        Formula according to PUS Standard: C = (Number of octets in packet data field) - 1.
        The size of the TC packet is the size of the packet secondary header with
        source ID + the length of the application data + length of the CRC16 checksum - 1
        """
        data_len = secondary_header_len + app_data_len
        if has_checksum:
            data_len += 2
        return data_len - 1

    @deprecation.deprecated(
        deprecated_in="v0.14.0rc3",
        current_version=get_version(),
        details="use pack and the class itself to build this instead",
    )
    def pack_command_tuple(self) -> tuple[bytearray, PusTc]:
        """Pack a tuple consisting of the raw packet as the first entry and the class representation
        as the second entry
        """
        return (self.pack(), self)

    @property
    def service(self) -> int:
        return self.pus_tc_sec_header.service

    @property
    def has_checksum(self) -> bool:
        return self._has_checksum

    @property
    def subservice(self) -> int:
        return self.pus_tc_sec_header.subservice

    @property
    def source_id(self) -> int:
        return self.pus_tc_sec_header.source_id

    @source_id.setter
    def source_id(self, source_id: int) -> None:
        self.pus_tc_sec_header.source_id = source_id

    @property
    def ccsds_version(self) -> int:
        return self.sp_header.ccsds_version

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
    def packet_seq_control(self) -> PacketSeqCtrl:
        return self.sp_header._psc

    @property
    def app_data(self) -> bytes:
        return bytes(self._app_data)

    @app_data.setter
    def app_data(self, app_data: bytes) -> None:
        self._app_data = app_data

    @property
    def crc16(self) -> bytes | None:
        """Will be the raw CRC16 if the telecommand was created using :py:meth:`unpack`,
        :py:meth:`pack` was called at least once or :py:meth:`calc_crc` was called at
        least once."""
        return self._crc16

    @seq_count.setter
    def seq_count(self, value: int) -> None:
        self.sp_header.seq_count = value

    @apid.setter
    def apid(self, apid: int) -> None:
        self.sp_header.apid = apid


PusTelecommand = PusTc


def generate_packet_crc(tc_packet: bytearray) -> bytes:
    """Removes current Packet Error Control, calculates new
    CRC16 checksum and adds it as correct Packet Error Control Code.
    Reference: ECSS-E70-41A p. 207-212
    """
    crc = crc16.ibm_3740(bytes(tc_packet[0 : len(tc_packet) - 2]))
    tc_packet[len(tc_packet) - 2] = (crc & 0xFF00) >> 8
    tc_packet[len(tc_packet) - 1] = crc & 0xFF
    return bytes(tc_packet)


def generate_crc(data: bytearray) -> bytes:
    """Takes the application data, appends the CRC16 checksum and returns resulting bytearray"""
    data_with_crc = bytearray()
    data_with_crc += data
    crc = crc16.ibm_3740(bytes(data))
    data_with_crc.extend(struct.pack("!H", crc))
    return bytes(data_with_crc)
