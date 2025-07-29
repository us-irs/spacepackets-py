"""This module contains import PUS TM packet classes, most notably the
:py:class:`spacepackets.ecss.tm.PusTelemetry` class.
"""

from __future__ import annotations

import struct

import deprecation
from fastcrc import crc16

from spacepackets.ccsds.spacepacket import (
    CCSDS_HEADER_LEN,
    SPACE_PACKET_HEADER_SIZE,
    PacketId,
    PacketSeqCtrl,
    PacketType,
    SequenceFlags,
    SpacePacket,
    SpacePacketHeader,
    get_total_space_packet_len_from_len_field,
)
from spacepackets.ccsds.time import CdsShortTimestamp
from spacepackets.ecss.defs import PusVersion
from spacepackets.ecss.tm import AbstractPusTm
from spacepackets.exceptions import BytesTooShortError
from spacepackets.util import PrintFormats, UnsignedByteField, get_printable_data_string
from spacepackets.version import get_version


class PusTmSecondaryHeader:
    """Unpacks the PUS telemetry packet secondary header.
    Currently only supports CDS short timestamps and PUS C"""

    MIN_LEN = 3

    def __init__(
        self,
        service: int,
        subservice: int,
        timestamp: bytes | bytearray,
        message_counter: int | None,
        dest_id: UnsignedByteField | None = None,
        spare_bytes: int = 0,
    ):
        """Create a PUS telemetry secondary header object.

        :param service:
        :param subservice:
        :param time_provider: Time field provider which can provide or read a time field
        :param message_counter: 8 bit counter for PUS A, 16 bit counter for PUS C
        :param dest_id: Destination ID if PUS C is used
        :param spacecraft_time_ref: Space time reference if PUS C is used
        """
        self.pus_version = PusVersion.PUS_A
        if service > pow(2, 8) - 1 or service < 0:
            raise ValueError(f"Invalid Service {service}")
        if subservice > pow(2, 8) - 1 or subservice < 0:
            raise ValueError(f"Invalid Subservice {subservice}")
        self.service = service
        self.subservice = subservice
        if message_counter is not None and (message_counter > pow(2, 8) - 1 or message_counter < 0):
            raise ValueError(
                f"Invalid message count value, larger than {pow(2, 16) - 1} or negative"
            )
        self.message_counter = message_counter
        self.dest_id = dest_id
        self.timestamp = bytes(timestamp)
        self.spare_bytes = spare_bytes

    @classmethod
    def __empty(cls) -> PusTmSecondaryHeader:
        return PusTmSecondaryHeader(
            service=0,
            subservice=0,
            timestamp=b"",
            message_counter=None,
        )

    def pack(self) -> bytearray:
        secondary_header = bytearray()
        secondary_header.append(self.pus_version << 4)
        secondary_header.append(self.service)
        secondary_header.append(self.subservice)
        if self.message_counter is not None:
            secondary_header.append(self.message_counter)
        if self.dest_id is not None:
            secondary_header.extend(self.dest_id.as_bytes)
        secondary_header.extend(self.timestamp)
        if self.spare_bytes > 0:
            secondary_header.extend(b"\x00" * self.spare_bytes)
        return secondary_header

    @classmethod
    def unpack(
        cls,
        data: bytes | bytearray,
        timestamp_len: int,
        has_message_counter: bool = False,
        dest_id_len: None | int = None,
        spare_bytes: int = 0,
    ) -> PusTmSecondaryHeader:
        """Unpack the PUS TM secondary header from the raw packet starting at the header index.

        :param data: Raw data. Please note that the passed buffer should start where the actual
            header start is.
        :param timestamp_len: Expected timestamp length.
        :raises ValueError: bytearray too short or PUS version missmatch.
        :return:
        """
        if len(data) < cls.MIN_LEN:
            raise BytesTooShortError(cls.MIN_LEN, len(data))
        secondary_header = cls.__empty()
        current_idx = 0
        secondary_header.pus_version = (data[current_idx] & 0xF0) >> 4
        if secondary_header.pus_version != PusVersion.PUS_A:
            raise ValueError(
                f"PUS version field value {secondary_header.pus_version} "
                f"found where PUS A {PusVersion.PUS_A} was expected"
            )
        if secondary_header.header_size > len(data):
            raise BytesTooShortError(secondary_header.header_size, len(data))
        current_idx += 1
        secondary_header.service = data[current_idx]
        current_idx += 1
        secondary_header.subservice = data[current_idx]
        current_idx += 1
        if has_message_counter:
            secondary_header.message_counter = data[current_idx]
            current_idx += 1
        if dest_id_len is not None:
            secondary_header.dest_id = UnsignedByteField.from_bytes(
                data[current_idx : current_idx + dest_id_len]
            )
        secondary_header.timestamp = data[current_idx : current_idx + timestamp_len]
        secondary_header.spare_bytes = spare_bytes
        return secondary_header

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(service={self.service!r},"
            f" subservice={self.subservice!r}, time={self.timestamp!r},"
            f" message_counter={self.message_counter!r}, dest_id={self.dest_id!r},"
            f" pus_version={self.pus_version!r}, spare_bytes={self.spare_bytes!r})"
        )

    def __eq__(self, other: object):
        if isinstance(other, PusTmSecondaryHeader):
            return (
                self.subservice == other.subservice
                and self.service == other.service
                and self.pus_version == other.pus_version
                and self.message_counter == other.message_counter
                and self.dest_id == other.dest_id
                and self.timestamp == other.timestamp
            )

        return False

    def __hash__(self) -> int:
        return hash(
            (
                self.subservice,
                self.service,
                self.pus_version,
                self.message_counter,
                self.dest_id,
                self.timestamp,
            )
        )

    @property
    def header_size(self) -> int:
        base_len = PusTmSecondaryHeader.MIN_LEN
        if self.timestamp:
            base_len += len(self.timestamp)
        if self.message_counter is not None:
            base_len += 1
        if self.dest_id is not None:
            base_len += self.dest_id.byte_len
        if self.spare_bytes > 0:
            base_len += self.spare_bytes
        return base_len


PUS_TM_TIMESTAMP_OFFSET = CCSDS_HEADER_LEN + PusTmSecondaryHeader.MIN_LEN


class InvalidTmCrc16Error(Exception):
    def __init__(self, tm: PusTm):
        self.tm = tm


class PusTm(AbstractPusTm):
    """Generic PUS telemetry class representation.

    Can be used to generate TM packets using a high level interface with the default constructor,
    or to deserialize TM packets from a raw byte stream using the :py:meth:`unpack` method.
    This implementation only supports PUS C.

    Deserialization of PUS telemetry requires the timestamp length to be known. If the size of the
    timestamp is variable but can be determined from the data, a look-ahead should be performed on
    the raw data. The :py:const:`PUS_TM_TIMESTAMP_OFFSET` (13) can be used to do this, assuming
    that the timestamp length can be extracted from the timestamp itself.

    The following doc example cuts off the timestamp (7 byte CDS Short) and the CRC16 from the ping
    packet because those change regularly.

    >>> ping_tm = PusTm(service=17, subservice=2, seq_count=5, apid=0x01, timestamp=CdsShortTimestamp.now().pack())
    >>> ping_tm.service
    17
    >>> ping_tm.subservice
    2
    >>> ping_tm.pack()[:-9].hex(sep=',')
    '08,01,c0,05,00,0b,10,11,02'
    """  # noqa: E501

    CDS_SHORT_SIZE = 7
    PUS_TIMESTAMP_SIZE = CDS_SHORT_SIZE

    def __init__(
        self,
        service: int,
        subservice: int,
        timestamp: bytes | bytearray,
        source_data: bytes | bytearray = b"",
        apid: int = 0,
        seq_count: int = 0,
        message_counter: int | None = None,
        destination_id: None | UnsignedByteField = None,
        packet_version: int = 0b000,
        sec_header_spare_bytes: int = 0,
    ):
        self._source_data = source_data
        len_stamp = len(timestamp)
        dest_id_len = None
        if destination_id is not None:
            dest_id_len = destination_id.byte_len
        data_length = self.data_len_from_src_len_timestamp_len(
            timestamp_len=len_stamp,
            source_data_len=len(self._source_data),
            has_message_counter=message_counter is not None,
            dest_id_len=dest_id_len,
        )
        self.space_packet_header = SpacePacketHeader(
            apid=apid,
            packet_type=PacketType.TM,
            sec_header_flag=True,
            ccsds_version=packet_version,
            data_len=data_length,
            seq_count=seq_count,
            seq_flags=SequenceFlags.UNSEGMENTED,
        )
        self.pus_tm_sec_header = PusTmSecondaryHeader(
            service=service,
            subservice=subservice,
            message_counter=message_counter,
            dest_id=destination_id,
            timestamp=timestamp,
            spare_bytes=sec_header_spare_bytes,
        )
        self._crc16: bytes | None = None

    @classmethod
    def empty(cls) -> PusTm:
        return PusTm(apid=0, service=0, subservice=0, timestamp=CdsShortTimestamp.empty().pack())

    def pack(self, recalc_crc: bool = True) -> bytearray:
        """Serializes the packet into a raw bytearray.

        :param recalc_crc: Can be set to False if the CRC was previous calculated and no fields were
            changed. This is set to True by default to ensure the CRC is always valid by default,
            even if the user changes arbitrary fields after TM creation.
        """
        tm_packet_raw = bytearray(self.space_packet_header.pack())
        tm_packet_raw.extend(self.pus_tm_sec_header.pack())
        tm_packet_raw.extend(self._source_data)
        if self._crc16 is None or recalc_crc:
            # CRC16-CCITT checksum
            self._crc16 = struct.pack("!H", crc16.ibm_3740(bytes(tm_packet_raw)))
        tm_packet_raw.extend(self._crc16)
        return tm_packet_raw

    def calc_crc(self) -> None:
        """Can be called to calculate the CRC16"""
        crc_calc = crc16.ibm_3740(bytes(self.space_packet_header.pack()))
        crc_calc = crc16.ibm_3740(bytes(self.pus_tm_sec_header.pack()), crc_calc)
        crc_calc = crc16.ibm_3740(bytes(self._source_data), crc_calc)
        self._crc16 = struct.pack("!H", crc_calc)

    @classmethod
    def unpack(
        cls,
        data: bytes | bytearray,
        timestamp_len: int,
        has_message_counter: bool,
        dest_id_len: int | None,
    ) -> PusTm:
        """Attempts to construct a generic PusTelemetry class given a raw bytearray.

        :param data: Raw bytes containing the PUS telemetry packet.
        :param time_reader: Time provider to read the timestamp. If the timestamp field is empty,
            you can supply None here.
        :raises BytesTooShortError: Passed bytestream too short.
        :raises ValueError: Unsupported PUS version.
        :raises InvalidTmCrc16Error: Invalid CRC16.
        """
        pus_tm = cls.empty()
        pus_tm.space_packet_header = SpacePacketHeader.unpack(data=data)
        expected_packet_len = get_total_space_packet_len_from_len_field(
            pus_tm.space_packet_header.data_len
        )
        if expected_packet_len > len(data):
            raise BytesTooShortError(expected_packet_len, len(data))
        pus_tm.pus_tm_sec_header = PusTmSecondaryHeader.unpack(
            data=data[SPACE_PACKET_HEADER_SIZE:],
            timestamp_len=timestamp_len,
            has_message_counter=has_message_counter,
            dest_id_len=dest_id_len,
        )
        if expected_packet_len < pus_tm.pus_tm_sec_header.header_size + SPACE_PACKET_HEADER_SIZE:
            raise ValueError("passed packet too short")
        pus_tm._source_data = data[
            pus_tm.pus_tm_sec_header.header_size + SPACE_PACKET_HEADER_SIZE : expected_packet_len
            - 2
        ]
        pus_tm._crc16 = bytes(data[expected_packet_len - 2 : expected_packet_len])
        # CRC16-CCITT checksum
        if crc16.ibm_3740(bytes(data[:expected_packet_len])) != 0:
            raise InvalidTmCrc16Error(pus_tm)
        return pus_tm

    @staticmethod
    def service_from_bytes(raw_bytearray: bytearray) -> int:
        """Determine the service ID from a raw packet, which can be used for packet deserialization.

        It is assumed that the user already checked that the raw bytearray contains a PUS packet and
        only basic sanity checks will be performed.
        :raise ValueError: If raw bytearray is too short
        """
        if len(raw_bytearray) < 8:
            raise ValueError
        return raw_bytearray[7]

    @classmethod
    def from_composite_fields(
        cls,
        sp_header: SpacePacketHeader,
        sec_header: PusTmSecondaryHeader,
        tm_data: bytes,
    ) -> PusTm:
        pus_tm = cls.empty()
        if sp_header.packet_type == PacketType.TC:
            raise ValueError(f"Invalid Packet Type {sp_header.packet_type} in CCSDS primary header")
        pus_tm.space_packet_header = sp_header
        pus_tm.pus_tm_sec_header = sec_header
        pus_tm._source_data = tm_data
        return pus_tm

    def to_space_packet(self) -> SpacePacket:
        """Retrieve the generic CCSDS space packet representation. This also calculates the CRC16
        before converting the PUS TC to a generic Space Packet"""
        self.calc_crc()
        user_data = bytearray(self._source_data)
        user_data.extend(self.crc16)  # type: ignore
        return SpacePacket(self.space_packet_header, self.pus_tm_sec_header.pack(), user_data)

    def __str__(self):
        return (
            f"PUS TM[{self.pus_tm_sec_header.service},"
            f"{self.pus_tm_sec_header.subservice}], APID {self.apid:#05x}, MSG Counter "
            f"{self.pus_tm_sec_header.message_counter}, Size {self.packet_len}"
        )

    def __repr__(self):
        return (
            f"{self.__class__.__name__}.from_composite_fields({self.__class__.__name__}"
            f"(sp_header={self.space_packet_header!r},"
            f" sec_header={self.pus_tm_sec_header!r}, tm_data={self.tm_data!r}"
        )

    def __eq__(self, other: object):
        if isinstance(other, PusTm):
            return (
                self.space_packet_header == other.space_packet_header
                and self.pus_tm_sec_header == other.pus_tm_sec_header
                and self._source_data == other._source_data
            )
        return False

    def __hash__(self) -> int:
        return hash(
            (
                self.space_packet_header,
                self.pus_tm_sec_header,
                self._source_data,
            )
        )

    @property
    def packet_seq_control(self) -> PacketSeqCtrl:
        return self.space_packet_header.packet_seq_control

    @property
    def sp_header(self) -> SpacePacketHeader:
        return self.space_packet_header

    @property
    def ccsds_version(self) -> int:
        return self.space_packet_header.ccsds_version

    @property
    def timestamp(self) -> bytes:
        return bytes(self.pus_tm_sec_header.timestamp)

    @property
    def service(self) -> int:
        """Get the service type ID
        :return: Service ID
        """
        return self.pus_tm_sec_header.service

    @property
    def subservice(self) -> int:
        """Get the subservice type ID
        :return: Subservice ID
        """
        return self.pus_tm_sec_header.subservice

    @property
    def source_data(self) -> bytes:
        return self.tm_data

    @property
    def tm_data(self) -> bytes:
        """
        :return: TM source data (raw)
        """
        return bytes(self._source_data)

    @tm_data.setter
    def tm_data(self, data: bytes) -> None:
        self._source_data = data
        stamp_len = len(self.pus_tm_sec_header.timestamp)
        dest_id_len = 0
        if self.pus_tm_sec_header.dest_id is not None:
            dest_id_len = self.pus_tm_sec_header.dest_id.byte_len
        self.space_packet_header.data_len = self.data_len_from_src_len_timestamp_len(
            stamp_len, len(data), self.pus_tm_sec_header.message_counter is not None, dest_id_len
        )

    @property
    def apid(self) -> int:
        return self.space_packet_header.apid

    @apid.setter
    def apid(self, apid: int) -> None:
        self.space_packet_header.apid = apid

    @property
    def seq_flags(self) -> SequenceFlags:
        return self.space_packet_header.seq_flags

    @seq_flags.setter
    def seq_flags(self, seq_flags: SequenceFlags) -> None:
        self.space_packet_header.seq_flags = seq_flags

    @property
    def packet_id(self) -> PacketId:
        return self.space_packet_header.packet_id

    @staticmethod
    def data_len_from_src_len_timestamp_len(
        timestamp_len: int, source_data_len: int, has_message_counter: bool, dest_id_len: None | int
    ) -> int:
        """Retrieve size of TM packet data header in bytes. Only support PUS C
        Formula according to PUS Standard: C = (Number of octets in packet source data field) - 1.
        The size of the TM packet is the size of the packet secondary header with
        the timestamp + the length of the application data + PUS timestamp size +
        length of the CRC16 checksum - 1

        :param source_data_len: Length of the source (user) data
        :param timestamp_len: Length of the used timestamp
        """
        data_len = PusTmSecondaryHeader.MIN_LEN + timestamp_len + source_data_len + 1
        if has_message_counter:
            data_len += 1
        if dest_id_len is not None:
            data_len += dest_id_len
        return data_len

    @property
    def packet_len(self) -> int:
        """Retrieve the full packet size when packed
        :return: Size of the TM packet based on the space packet header data length field.
        The space packet data field is the full length of data field minus one without
        the space packet header.
        """
        return self.space_packet_header.packet_len

    @property
    def seq_count(self) -> int:
        """Get the source sequence count
        :return: Source Sequence Count (see below, or PUS documentation)
        """
        return self.space_packet_header.seq_count

    @property
    def crc16(self) -> bytes | None:
        """Will be the raw CRC16 if the telecommand was created using :py:meth:`unpack` or
        :py:meth:`pack` was called at least once."""
        return self._crc16

    @deprecation.deprecated(
        deprecated_in="0.14.0rc3",
        current_version=get_version(),
        details=("use pack and get_printable_data_string or the hex method on bytearray instead"),
    )
    def get_full_packet_string(self, print_format: PrintFormats = PrintFormats.HEX) -> str:
        packet_raw = self.pack()
        return get_printable_data_string(print_format=print_format, data=packet_raw)

    @deprecation.deprecated(
        deprecated_in="0.14.0rc3",
        current_version=get_version(),
        details=("use pack and get_printable_data_string or the hex method on bytearray instead"),
    )
    def print_full_packet_string(self, print_format: PrintFormats = PrintFormats.HEX) -> None:
        """Print the full TM packet in a clean format."""
        print(self.get_full_packet_string(print_format=print_format))

    @deprecation.deprecated(
        deprecated_in="0.14.0rc3",
        current_version=get_version(),
        details=("use print, the source_data property and the hex method on bytearray instead"),
    )
    def print_source_data(self, print_format: PrintFormats = PrintFormats.HEX) -> None:
        """Prints the TM source data in a clean format"""
        print(self.get_source_data_string(print_format=print_format))

    @deprecation.deprecated(
        deprecated_in="0.14.0rc3",
        current_version=get_version(),
        details="use the source_data property and the hex method on bytearray instead",
    )
    def get_source_data_string(self, print_format: PrintFormats = PrintFormats.HEX) -> str:
        """Returns the source data string"""
        return get_printable_data_string(print_format=print_format, data=self._source_data)


PusTelemetry = PusTm
