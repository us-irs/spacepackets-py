from __future__ import annotations

from crcmod.predefined import mkPredefinedCrcFun

from spacepackets.util import PrintFormats, get_printable_data_string
from spacepackets.log import get_console_logger
from spacepackets.ccsds.spacepacket import (
    SpacePacketHeader,
    SPACE_PACKET_HEADER_SIZE,
    get_total_space_packet_len_from_len_field,
    PacketTypes,
)
from spacepackets.ccsds.time import CdsShortTimestamp, read_p_field
from spacepackets.ecss.conf import get_pus_tm_version, PusVersion, get_default_tm_apid


def get_service_from_raw_pus_packet(raw_bytearray: bytearray) -> int:
    """Determine the service ID from a raw packet, which can be used for packet deserialization.

    It is assumed that the user already checked that the raw bytearray contains a PUS packet and
    only basic sanity checks will be performed.
    :raise ValueError: If raw bytearray is too short
    """
    if len(raw_bytearray) < 8:
        raise ValueError
    return raw_bytearray[7]


class PusTelemetry:
    """Generic PUS telemetry class representation.
    It is instantiated by passing the raw pus telemetry packet (bytearray) to the constructor.
    It automatically deserializes the packet, exposing various packet fields via getter functions.
    PUS Telemetry structure according to ECSS-E-70-41A p.46. Also see structure below (bottom).
    """

    CDS_SHORT_SIZE = 7
    PUS_TIMESTAMP_SIZE = CDS_SHORT_SIZE

    def __init__(
        self,
        service: int,
        subservice: int,
        time: CdsShortTimestamp = None,
        ssc: int = 0,
        source_data: bytearray = bytearray([]),
        apid: int = -1,
        message_counter: int = 0,
        space_time_ref: int = 0b0000,
        destination_id: int = 0,
        packet_version: int = 0b000,
        pus_version: PusVersion = PusVersion.GLOBAL_CONFIG,
        secondary_header_flag: bool = True,
    ):
        if apid == -1:
            apid = get_default_tm_apid()
        if pus_version == PusVersion.GLOBAL_CONFIG:
            pus_version = get_pus_tm_version()
        if time is None:
            time = CdsShortTimestamp.init_from_current_time()
        # packet type for telemetry is 0 as specified in standard
        # specified in standard
        packet_type = PacketTypes.TM
        self._source_data = source_data
        data_length = self.get_source_data_length(
            timestamp_len=PusTelemetry.PUS_TIMESTAMP_SIZE, pus_version=pus_version
        )
        self.space_packet_header = SpacePacketHeader(
            apid=apid,
            packet_type=packet_type,
            secondary_header_flag=secondary_header_flag,
            packet_version=packet_version,
            data_length=data_length,
            source_sequence_count=ssc,
        )
        self.secondary_packet_header = PusTmSecondaryHeader(
            pus_version=pus_version,
            service_id=service,
            subservice_id=subservice,
            message_counter=message_counter,
            destination_id=destination_id,
            spacecraft_time_ref=space_time_ref,
            time=time,
        )
        self._valid = True
        self._crc16 = 0

    @classmethod
    def __empty(
        cls, pus_version: PusVersion = PusVersion.GLOBAL_CONFIG
    ) -> PusTelemetry:
        return PusTelemetry(
            service=0, subservice=0, time=CdsShortTimestamp.init_from_current_time()
        )

    def pack(self) -> bytearray:
        """Serializes the PUS telemetry into a raw packet."""
        tm_packet_raw = bytearray()
        # PUS Header
        tm_packet_raw.extend(self.space_packet_header.pack())
        # PUS Source Data Field
        tm_packet_raw.extend(self.secondary_packet_header.pack())
        # Source Data
        tm_packet_raw.extend(self._source_data)
        # CRC16-CCITT checksum
        crc_func = mkPredefinedCrcFun(crc_name="crc-ccitt-false")
        self._crc16 = crc_func(tm_packet_raw)
        tm_packet_raw.append((self._crc16 & 0xFF00) >> 8)
        tm_packet_raw.append(self._crc16 & 0xFF)
        return tm_packet_raw

    @classmethod
    def unpack(
        cls,
        raw_telemetry: bytearray,
        pus_version: PusVersion = PusVersion.GLOBAL_CONFIG,
    ) -> PusTelemetry:
        """Attempts to construct a generic PusTelemetry class given a raw bytearray.
        :param pus_version:
        :raises ValueError: if the format of the raw bytearray is invalid, for example the length
        :param raw_telemetry:
        """
        if raw_telemetry is None:
            logger = get_console_logger()
            logger.warning("Given byte stream invalid!")
            raise ValueError
        elif len(raw_telemetry) == 0:
            logger = get_console_logger()
            logger.warning("Given byte stream is empty")
            raise ValueError
        pus_tm = cls.__empty(pus_version=pus_version)
        pus_tm._valid = False
        pus_tm.space_packet_header = SpacePacketHeader.unpack(
            space_packet_raw=raw_telemetry
        )
        expected_packet_len = get_total_space_packet_len_from_len_field(
            pus_tm.space_packet_header.data_length
        )
        if expected_packet_len > len(raw_telemetry):
            logger = get_console_logger()
            logger.warning(
                f"PusTelemetry: Passed packet with length {len(raw_telemetry)} "
                f"shorter than specified packet length in PUS header {expected_packet_len}"
            )
            raise ValueError
        pus_tm.secondary_packet_header = PusTmSecondaryHeader.unpack(
            header_start=raw_telemetry[SPACE_PACKET_HEADER_SIZE:],
            pus_version=pus_version,
        )
        if (
            expected_packet_len
            < pus_tm.secondary_packet_header.header_size + SPACE_PACKET_HEADER_SIZE
        ):
            logger = get_console_logger()
            logger.warning("Passed packet too short!")
            raise ValueError
        if pus_tm.packet_len != len(raw_telemetry):
            logger = get_console_logger()
            logger.warning(
                f"PusTelemetry: Packet length field "
                f"{pus_tm.space_packet_header.data_length} might be invalid!"
            )
            logger.warning(f"Packet size from size field: {pus_tm.packet_len}")
            logger.warning(f"Length of raw telemetry: {len(raw_telemetry)}")
        pus_tm._source_data = raw_telemetry[
            pus_tm.secondary_packet_header.header_size + SPACE_PACKET_HEADER_SIZE : -2
        ]
        pus_tm._crc = (
            raw_telemetry[expected_packet_len - 2] << 8
            | raw_telemetry[expected_packet_len - 1]
        )
        pus_tm.__perform_crc_check(raw_telemetry=raw_telemetry[:expected_packet_len])
        return pus_tm

    def __str__(self):
        return (
            f"PUS TM[{self.secondary_packet_header.service_id},"
            f"{self.secondary_packet_header.subservice_id}] with message counter "
            f"{self.secondary_packet_header.message_counter}"
        )

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(service={self.secondary_packet_header.service_id!r}, "
            f"subservice={self.secondary_packet_header.subservice_id!r}, "
            f"apid={self.apid!r}, ssc={self.ssc!r})"
        )

    @property
    def service(self) -> int:
        """Get the service type ID
        :return: Service ID
        """
        return self.secondary_packet_header.service_id

    @property
    def subservice(self) -> int:
        """Get the subservice type ID
        :return: Subservice ID
        """
        return self.secondary_packet_header.subservice_id

    @property
    def valid(self) -> bool:
        return self._valid

    @property
    def tm_data(self) -> bytearray:
        """
        :return: TM application data (raw)
        """
        return self._source_data

    @property
    def packet_id(self) -> int:
        return self.space_packet_header.packet_id

    def __perform_crc_check(self, raw_telemetry: bytes):
        # CRC16-CCITT checksum
        crc_func = mkPredefinedCrcFun(crc_name="crc-ccitt-false")
        full_packet_size = self.packet_len
        data_to_check = raw_telemetry[:full_packet_size]
        crc = crc_func(data_to_check)
        if crc == 0:
            self._valid = True
        else:
            logger = get_console_logger()
            logger.warning("Invalid CRC detected !")
            self._valid = False

    def get_source_data_length(
        self, timestamp_len: int, pus_version: PusVersion
    ) -> int:
        """Retrieve size of TM packet data header in bytes.
        Formula according to PUS Standard: C = (Number of octets in packet source data field) - 1.
        The size of the TM packet is the size of the packet secondary header with
        the timestamp + the length of the application data + PUS timestamp size +
        length of the CRC16 checksum - 1

        :param timestamp_len: Length of the used timestamp
        :param pus_version: Used PUS version
        :raises ValueError: Invalid PUS version
        """
        if pus_version == PusVersion.PUS_A:
            data_length = (
                PusTmSecondaryHeader.HEADER_SIZE_WITHOUT_TIME_PUS_A
                + timestamp_len
                + len(self._source_data)
                + 1
            )
        elif pus_version == PusVersion.PUS_C:
            data_length = (
                PusTmSecondaryHeader.HEADER_SIZE_WITHOUT_TIME_PUS_C
                + timestamp_len
                + len(self._source_data)
                + 1
            )
        else:
            logger = get_console_logger()
            logger.warning(f"PUS version {pus_version} not supported")
            raise ValueError
        return data_length

    @property
    def packet_len(self) -> int:
        """Retrieve the full packet size when packed
        :return: Size of the TM packet based on the space packet header data length field.
        The space packet data field is the full length of data field minus one without
        the space packet header.
        """
        return self.space_packet_header.packet_len

    @property
    def apid(self) -> int:
        return self.space_packet_header.apid

    @property
    def ssc(self) -> int:
        """Get the source sequence count
        :return: Source Sequence Count (see below, or PUS documentation)
        """
        return self.space_packet_header.ssc

    @property
    def crc16(self) -> int:
        return self._crc16

    def get_full_packet_string(self, print_format: PrintFormats) -> str:
        packet_raw = self.pack()
        return get_printable_data_string(
            print_format=print_format, data=packet_raw, length=len(packet_raw)
        )

    def print_full_packet_string(self, print_format: PrintFormats):
        """Print the full TM packet in a clean format."""
        print(self.get_full_packet_string(print_format=print_format))

    def print_source_data(self, print_format: PrintFormats):
        """Prints the TM source data in a clean format"""
        print(self.get_source_data_string(print_format=print_format))

    def get_source_data_string(self, print_format: PrintFormats) -> str:
        """Returns the source data string"""
        return get_printable_data_string(
            print_format=print_format,
            data=self._source_data,
            length=len(self._source_data),
        )


class PusTmSecondaryHeader:
    """Unpacks the PUS telemetry packet secondary header.
    Currently only supports CDS short timestamps"""

    HEADER_SIZE_WITHOUT_TIME_PUS_A = 4
    HEADER_SIZE_WITHOUT_TIME_PUS_C = 7

    def __init__(
        self,
        service_id: int,
        subservice_id: int,
        time: CdsShortTimestamp,
        message_counter: int,
        destination_id: int = 0,
        spacecraft_time_ref: int = 0,
        pus_version: PusVersion = PusVersion.GLOBAL_CONFIG,
    ):
        """Create a PUS telemetry secondary header object.

        :param pus_version: PUS version. ESA PUS is not supported
        :param service_id:
        :param subservice_id:
        :param time: Time field
        :param message_counter: 8 bit counter for PUS A, 16 bit counter for PUS C
        :param destination_id: Destination ID if PUS C is used
        :param spacecraft_time_ref: Space time reference if PUS C is used
        """
        self.pus_version = pus_version
        if self.pus_version == PusVersion.GLOBAL_CONFIG:
            self.pus_version = get_pus_tm_version()
        if (
            self.pus_version != PusVersion.PUS_A
            and self.pus_version != PusVersion.PUS_C
        ):
            raise ValueError
        self.spacecraft_time_ref = spacecraft_time_ref
        self.service_id = service_id
        self.subservice_id = subservice_id
        if (
            self.pus_version == PusVersion.PUS_A and message_counter > pow(2, 8) - 1
        ) or (
            self.pus_version == PusVersion.PUS_C and message_counter > pow(2, 16) - 1
        ):
            raise ValueError
        self.message_counter = message_counter
        self.destination_id = destination_id
        self.time = time

    @classmethod
    def __empty(cls) -> PusTmSecondaryHeader:
        return PusTmSecondaryHeader(
            pus_version=PusVersion.PUS_C,
            service_id=-1,
            subservice_id=-1,
            time=CdsShortTimestamp.init_from_current_time(),
            message_counter=0,
        )

    def pack(self) -> bytearray:
        secondary_header = bytearray()
        if self.pus_version == PusVersion.PUS_A:
            secondary_header.append((self.pus_version & 0x07) << 4)
        elif self.pus_version == PusVersion.PUS_C:
            secondary_header.append(self.pus_version << 4 | self.spacecraft_time_ref)
        secondary_header.append(self.service_id)
        secondary_header.append(self.subservice_id)
        if self.pus_version == PusVersion.PUS_A:
            secondary_header.append(self.message_counter)
        elif self.pus_version == PusVersion.PUS_C:
            secondary_header.append((self.message_counter & 0xFF00) >> 8)
            secondary_header.append(self.message_counter & 0xFF)
            secondary_header.append((self.destination_id & 0xFF00) >> 8)
            secondary_header.append(self.destination_id & 0xFF)
        secondary_header.extend(self.time.pack())
        return secondary_header

    @classmethod
    def unpack(
        cls, header_start: bytearray, pus_version: PusVersion
    ) -> PusTmSecondaryHeader:
        """Unpack the PUS TM secondary header from the raw packet starting at the header index.
        The user still needs to specify the PUS version because the version field is parsed
        differently depending on the PUS version.

        :param header_start:
        :param pus_version:
        :raises ValueError: bytearray too short or PUS version missmatch.
        :return:
        """
        if len(header_start) < cls.HEADER_SIZE_WITHOUT_TIME_PUS_A:
            logger = get_console_logger()
            logger.warning("Passed bytearray too short")
            raise ValueError
        if pus_version == PusVersion.GLOBAL_CONFIG:
            pus_version = get_pus_tm_version()
        secondary_header = cls.__empty()
        current_idx = 0
        if pus_version == PusVersion.PUS_A:
            secondary_header.pus_version = (header_start[current_idx] & 0x70) >> 4
            if secondary_header.pus_version != PusVersion.PUS_A:
                logger = get_console_logger()
                logger.warning(
                    f"PUS version field value {secondary_header.pus_version} "
                    f"found where PUS A {pus_version} was expected!"
                )
                raise ValueError
        elif pus_version == PusVersion.PUS_C:
            secondary_header.pus_version = (header_start[current_idx] & 0xF0) >> 4
            if secondary_header.pus_version != PusVersion.PUS_C:
                logger = get_console_logger()
                logger.warning(
                    f"PUS version field value {secondary_header.pus_version} "
                    f"found where PUS C {pus_version} was expected!"
                )
                raise ValueError
            secondary_header.spacecraft_time_ref = header_start[current_idx] & 0x0F
        if len(header_start) < secondary_header.header_size:
            logger = get_console_logger()
            logger.warning(
                f"Invalid PUS data field header size, "
                f"less than expected {secondary_header.header_size} bytes"
            )
            raise ValueError
        current_idx += 1
        secondary_header.service_id = header_start[current_idx]
        current_idx += 1
        secondary_header.subservice_id = header_start[current_idx]
        current_idx += 1
        if pus_version == PusVersion.PUS_A:
            secondary_header.message_counter = header_start[current_idx]
            current_idx += 1
        else:
            secondary_header.message_counter = (
                header_start[current_idx] << 8 | header_start[current_idx + 1]
            )
            current_idx += 2
        if pus_version == PusVersion.PUS_C:
            secondary_header.destination_id = (
                header_start[current_idx] << 8 | header_start[current_idx + 1]
            )
            current_idx += 2
        # If other time formats are supported in the future, this information can be used
        #  to unpack the correct time code
        time_code_id = read_p_field(header_start[current_idx])
        if time_code_id:
            pass
        secondary_header.time = CdsShortTimestamp.unpack(
            time_field=header_start[
                current_idx : current_idx + PusTelemetry.PUS_TIMESTAMP_SIZE
            ]
        )
        return secondary_header

    @property
    def header_size(self) -> int:
        if self.pus_version == PusVersion.PUS_A:
            return PusTelemetry.PUS_TIMESTAMP_SIZE + 4
        else:
            return PusTelemetry.PUS_TIMESTAMP_SIZE + 7
