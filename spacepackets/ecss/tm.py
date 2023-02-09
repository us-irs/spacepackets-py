"""This module contains import PUS TM packet classes, most notably the
:py:class:`spacepackets.ecss.tm.PusTelemetry` class.
"""
from __future__ import annotations

from abc import abstractmethod
import struct
from typing import Optional

import deprecation
from crcmod.predefined import PredefinedCrc

from .exceptions import TmSrcDataTooShortError  # noqa  # re-export
from spacepackets import __version__
from spacepackets.ccsds.time.common import read_p_field
from spacepackets.exceptions import BytesTooShortError
from spacepackets.util import PrintFormats, get_printable_data_string
from spacepackets.ccsds.spacepacket import (
    SpacePacketHeader,
    SPACE_PACKET_HEADER_SIZE,
    get_total_space_packet_len_from_len_field,
    PacketType,
    SpacePacket,
    AbstractSpacePacket,
    SequenceFlags,
)
from spacepackets.ccsds.time import CdsShortTimestamp, CcsdsTimeProvider
from spacepackets.ecss.conf import (
    PusVersion,
    get_default_tm_apid,
    FETCH_GLOBAL_APID,
)
from spacepackets.ecss.crc import CRC16_CCITT_FUNC


class AbstractPusTm(AbstractSpacePacket):
    """Generic abstraction for PUS TM packets"""

    @property
    @abstractmethod
    def sp_header(self) -> SpacePacketHeader:
        pass

    @deprecation.deprecated(
        deprecated_in="v0.14.0rc2",
        details="use sp_header property instead",
        current_version=__version__,
    )
    def get_sp_header(self) -> SpacePacketHeader:
        return self.sp_header

    @property
    @abstractmethod
    def service(self) -> int:
        pass

    @property
    @abstractmethod
    def time_provider(self) -> Optional[CcsdsTimeProvider]:
        pass

    @property
    @abstractmethod
    def subservice(self) -> int:
        pass

    @property
    def apid(self) -> int:
        return self.sp_header.apid

    @property
    def seq_count(self) -> int:
        return self.sp_header.seq_count

    @property
    @abstractmethod
    def source_data(self) -> bytes:
        pass


class PusTmSecondaryHeader:
    """Unpacks the PUS telemetry packet secondary header.
    Currently only supports CDS short timestamps and PUS C"""

    MIN_LEN = 7

    def __init__(
        self,
        service: int,
        subservice: int,
        time_provider: Optional[CcsdsTimeProvider],
        message_counter: int,
        dest_id: int = 0,
        spacecraft_time_ref: int = 0,
    ):
        """Create a PUS telemetry secondary header object.

        :param service:
        :param subservice:
        :param time_provider: Time field provider which can provide or read a time field
        :param message_counter: 8 bit counter for PUS A, 16 bit counter for PUS C
        :param dest_id: Destination ID if PUS C is used
        :param spacecraft_time_ref: Space time reference if PUS C is used
        """
        self.pus_version = PusVersion.PUS_C
        self.spacecraft_time_ref = spacecraft_time_ref
        if service > pow(2, 8) - 1 or service < 0:
            raise ValueError(f"Invalid Service {service}")
        if subservice > pow(2, 8) - 1 or subservice < 0:
            raise ValueError(f"Invalid Subservice {subservice}")
        self.service = service
        self.subservice = subservice
        if message_counter > pow(2, 16) - 1 or message_counter < 0:
            raise ValueError(
                f"Invalid message count value, larger than {pow(2, 16) - 1} or negative"
            )
        self.message_counter = message_counter
        self.dest_id = dest_id
        self.time_provider = time_provider

    @classmethod
    def __empty(cls) -> PusTmSecondaryHeader:
        return PusTmSecondaryHeader(
            service=0,
            subservice=0,
            time_provider=CdsShortTimestamp.from_now(),
            message_counter=0,
        )

    def pack(self) -> bytearray:
        secondary_header = bytearray()
        secondary_header.append(self.pus_version << 4 | self.spacecraft_time_ref)
        secondary_header.append(self.service)
        secondary_header.append(self.subservice)
        secondary_header.extend(struct.pack("!H", self.message_counter))
        secondary_header.extend(struct.pack("!H", self.dest_id))
        if self.time_provider:
            secondary_header.extend(self.time_provider.pack())
        return secondary_header

    @classmethod
    def unpack(
        cls, data: bytes, time_reader: Optional[CcsdsTimeProvider]
    ) -> PusTmSecondaryHeader:
        """Unpack the PUS TM secondary header from the raw packet starting at the header index.

        :param data: Raw data. Please note that the passed buffer should start where the actual
            header start is.
        :param time_reader: Generic time reader which knows the time stamp size and how to interpret
            the raw timestamp
        :raises ValueError: bytearray too short or PUS version missmatch.
        :return:
        """
        if len(data) < cls.MIN_LEN:
            raise BytesTooShortError(cls.MIN_LEN, len(data))
        secondary_header = cls.__empty()
        current_idx = 0
        secondary_header.pus_version = (data[current_idx] & 0xF0) >> 4
        if secondary_header.pus_version != PusVersion.PUS_C:
            raise ValueError(
                f"PUS version field value {secondary_header.pus_version} "
                f"found where PUS C {PusVersion.PUS_C} was expected"
            )
        secondary_header.spacecraft_time_ref = data[current_idx] & 0x0F
        if secondary_header.header_size > len(data):
            raise BytesTooShortError(secondary_header.header_size, len(data))
        current_idx += 1
        secondary_header.service = data[current_idx]
        current_idx += 1
        secondary_header.subservice = data[current_idx]
        current_idx += 1
        secondary_header.message_counter = struct.unpack(
            "!H", data[current_idx : current_idx + 2]
        )[0]
        current_idx += 2
        secondary_header.dest_id = struct.unpack(
            "!H", data[current_idx : current_idx + 2]
        )[0]
        current_idx += 2
        # If other time formats are supported in the future, this information can be used
        #  to unpack the correct time code
        time_code_id = read_p_field(data[current_idx])
        if time_code_id:
            pass
        if time_reader:
            time_reader.read_from_raw(
                data[current_idx : current_idx + time_reader.len_packed]
            )
        secondary_header.time_provider = time_reader
        return secondary_header

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(service={self.service!r}, subservice={self.subservice!r}, "
            f"time={self.time_provider!r}, message_counter={self.message_counter!r}, "
            f"dest_id={self.dest_id!r}, spacecraft_time_ref={self.spacecraft_time_ref!r}, "
            f"pus_version={self.pus_version!r})"
        )

    def __eq__(self, other: PusTmSecondaryHeader):
        return self.pack() == other.pack()

    @property
    def header_size(self) -> int:
        base_len = 7
        if self.time_provider:
            base_len += self.time_provider.len_packed
        return base_len


class InvalidTmCrc16(Exception):
    def __init__(self, tm: PusTelemetry):
        self.tm = tm


class PusTelemetry(AbstractPusTm):
    """Generic PUS telemetry class representation.

    Can be used to generate TM packets using a high level interface with the default constructor,
    or to deserialize TM packets from a raw byte stream using the :py:meth:`unpack` method.
    This implementation only supports PUS C.

    The following doc example cuts off the timestamp (7 byte CDS Short) and the CRC16 from the ping
    packet because those change regularly.

    >>> ping_tm = PusTelemetry(service=17, subservice=2, seq_count=5, apid=0x01, time_provider=CdsShortTimestamp.empty()) # noqa
    >>> ping_tm.service
    17
    >>> ping_tm.subservice
    2
    >>> ping_tm.pack()[:-9].hex(sep=',')
    '08,01,c0,05,00,0f,20,11,02,00,00,00,00'
    """

    CDS_SHORT_SIZE = 7
    PUS_TIMESTAMP_SIZE = CDS_SHORT_SIZE

    # TODO: Supply this constructor as a classmethod in reduced form
    def __init__(
        self,
        service: int,
        subservice: int,
        time_provider: Optional[CcsdsTimeProvider],
        source_data: bytes = bytes([]),
        seq_count: int = 0,
        apid: int = FETCH_GLOBAL_APID,
        message_counter: int = 0,
        space_time_ref: int = 0b0000,
        destination_id: int = 0,
        packet_version: int = 0b000,
    ):
        if apid == FETCH_GLOBAL_APID:
            apid = get_default_tm_apid()
        self._source_data = source_data
        len_stamp = 0
        if time_provider:
            len_stamp += time_provider.len_packed
        data_length = self.data_len_from_src_len_timestamp_len(
            timestamp_len=len_stamp,
            source_data_len=len(self._source_data),
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
            spacecraft_time_ref=space_time_ref,
            time_provider=time_provider,
        )
        self._crc16: Optional[bytes] = None

    @classmethod
    def empty(cls) -> PusTelemetry:
        return PusTelemetry(
            service=0, subservice=0, time_provider=CdsShortTimestamp.empty()
        )

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
            self._crc16 = struct.pack("!H", CRC16_CCITT_FUNC(tm_packet_raw))
        tm_packet_raw.extend(self._crc16)
        return tm_packet_raw

    def calc_crc(self):
        """Can be called to calculate the CRC16"""
        crc = PredefinedCrc(crc_name="crc-ccitt-false")
        crc.update(self.space_packet_header.pack())
        crc.update(self.pus_tm_sec_header.pack())
        crc.update(self._source_data)
        self._crc16 = struct.pack("!H", crc.crcValue)

    @classmethod
    def unpack(
        cls, data: bytes, time_reader: Optional[CcsdsTimeProvider]
    ) -> PusTelemetry:
        """Attempts to construct a generic PusTelemetry class given a raw bytearray.

        :param data: Raw bytes containing the PUS telemetry packet.
        :param time_reader: Time provider to read the timestamp. If the timestamp field is empty,
            you can supply None here.
        :raises BytesTooShortError: Passed bytestream too short.
        :raises ValueError: Unsupported PUS version.
        :raises InvalidTmCrc16: Invalid CRC16.
        """
        if data is None:
            raise ValueError("byte stream invalid")
        pus_tm = cls.empty()
        pus_tm.space_packet_header = SpacePacketHeader.unpack(data=data)
        expected_packet_len = get_total_space_packet_len_from_len_field(
            pus_tm.space_packet_header.data_len
        )
        if expected_packet_len > len(data):
            raise BytesTooShortError(expected_packet_len, len(data))
        pus_tm.pus_tm_sec_header = PusTmSecondaryHeader.unpack(
            data=data[SPACE_PACKET_HEADER_SIZE:],
            time_reader=time_reader,
        )
        if (
            expected_packet_len
            < pus_tm.pus_tm_sec_header.header_size + SPACE_PACKET_HEADER_SIZE
        ):
            raise ValueError("passed packet too short")
        pus_tm._source_data = data[
            pus_tm.pus_tm_sec_header.header_size
            + SPACE_PACKET_HEADER_SIZE : expected_packet_len
            - 2
        ]
        pus_tm._crc16 = data[expected_packet_len - 2 : expected_packet_len]
        # CRC16-CCITT checksum
        if CRC16_CCITT_FUNC(data[:expected_packet_len]) != 0:
            raise InvalidTmCrc16(pus_tm)
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
    ) -> PusTelemetry:
        pus_tm = cls.empty()
        if sp_header.packet_type == PacketType.TC:
            raise ValueError(
                f"Invalid Packet Type {sp_header.packet_type} in CCSDS primary header"
            )
        pus_tm.space_packet_header = sp_header
        pus_tm.pus_tm_sec_header = sec_header
        pus_tm._source_data = tm_data
        return pus_tm

    def to_space_packet(self) -> SpacePacket:
        """Retrieve the generic CCSDS space packet representation. This also calculates the CRC16
        before converting the PUS TC to a generic Space Packet"""
        self.calc_crc()
        user_data = bytearray(self._source_data)
        user_data.extend(self.crc16)
        return SpacePacket(
            self.space_packet_header, self.pus_tm_sec_header.pack(), user_data
        )

    def __str__(self):
        return (
            f"PUS TM[{self.pus_tm_sec_header.service},"
            f"{self.pus_tm_sec_header.subservice}], APID {self.apid:#05x}, MSG Counter "
            f"{self.pus_tm_sec_header.message_counter}, Size {self.packet_len}"
        )

    def __repr__(self):
        return (
            f"{self.__class__.__name__}.from_composite_fields({self.__class__.__name__}"
            f"(sp_header={self.space_packet_header!r}, sec_header={self.pus_tm_sec_header!r}, "
            f"tm_data={self.tm_data!r}"
        )

    def __eq__(self, other: PusTelemetry):
        return (
            self.space_packet_header == other.space_packet_header
            and self.pus_tm_sec_header == other.pus_tm_sec_header
            and self._source_data == other._source_data
        )

    @property
    def sp_header(self) -> SpacePacketHeader:
        return self.space_packet_header

    @property
    def time_provider(self) -> Optional[CcsdsTimeProvider]:
        return self.pus_tm_sec_header.time_provider

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
        return self._source_data

    @tm_data.setter
    def tm_data(self, data: bytes):
        self._source_data = data
        stamp_len = 0
        if self.pus_tm_sec_header.time_provider:
            stamp_len += self.pus_tm_sec_header.time_provider.len_packed
        self.space_packet_header.data_len = self.data_len_from_src_len_timestamp_len(
            stamp_len, len(data)
        )

    @property
    def apid(self):
        return self.space_packet_header.apid

    @apid.setter
    def apid(self, apid: int):
        self.space_packet_header.apid = apid

    @property
    def seq_flags(self):
        return self.space_packet_header.seq_flags

    @seq_flags.setter
    def seq_flags(self, seq_flags):
        self.space_packet_header.seq_flags = seq_flags

    @property
    def packet_id(self):
        return self.space_packet_header.packet_id

    @staticmethod
    def data_len_from_src_len_timestamp_len(
        timestamp_len: int, source_data_len: int
    ) -> int:
        """Retrieve size of TM packet data header in bytes. Only support PUS C
        Formula according to PUS Standard: C = (Number of octets in packet source data field) - 1.
        The size of the TM packet is the size of the packet secondary header with
        the timestamp + the length of the application data + PUS timestamp size +
        length of the CRC16 checksum - 1

        :param source_data_len: Length of the source (user) data
        :param timestamp_len: Length of the used timestamp
        """
        return PusTmSecondaryHeader.MIN_LEN + timestamp_len + source_data_len + 1

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
    def crc16(self) -> Optional[bytes]:
        """Will be the raw CRC16 if the telecommand was created using :py:meth:`unpack` or
        :py:meth:`pack` was called at least once."""
        return self._crc16

    @deprecation.deprecated(
        deprecated_in="0.14.0rc3",
        current_version=__version__,
        details="use pack and get_printable_data_string or the hex method on bytearray instead",
    )
    def get_full_packet_string(
        self, print_format: PrintFormats = PrintFormats.HEX
    ) -> str:
        packet_raw = self.pack()
        return get_printable_data_string(print_format=print_format, data=packet_raw)

    @deprecation.deprecated(
        deprecated_in="0.14.0rc3",
        current_version=__version__,
        details="use pack and get_printable_data_string or the hex method on bytearray instead",
    )
    def print_full_packet_string(self, print_format: PrintFormats = PrintFormats.HEX):
        """Print the full TM packet in a clean format."""
        print(self.get_full_packet_string(print_format=print_format))

    @deprecation.deprecated(
        deprecated_in="0.14.0rc3",
        current_version=__version__,
        details="use print, the source_data property and the hex method on bytearray instead",
    )
    def print_source_data(self, print_format: PrintFormats = PrintFormats.HEX):
        """Prints the TM source data in a clean format"""
        print(self.get_source_data_string(print_format=print_format))

    @deprecation.deprecated(
        deprecated_in="0.14.0rc3",
        current_version=__version__,
        details="use the source_data property and the hex method on bytearray instead",
    )
    def get_source_data_string(
        self, print_format: PrintFormats = PrintFormats.HEX
    ) -> str:
        """Returns the source data string"""
        return get_printable_data_string(
            print_format=print_format, data=self._source_data
        )
