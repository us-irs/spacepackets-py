from __future__ import annotations

from crcmod import crcmod

from spacepackets.log import get_console_logger
from spacepackets.ccsds.spacepacket import SpacePacketHeader, SPACE_PACKET_HEADER_SIZE, \
    get_total_space_packet_len_from_len_field, PacketTypes
from spacepackets.ccsds.time import CdsShortTimestamp, read_p_field
from spacepackets.ecss.conf import get_pus_tm_version, PusVersion, get_tm_apid


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
            self, service_id: int, subservice_id: int, time: CdsShortTimestamp = None, ssc: int = 0,
            source_data: bytearray = bytearray([]), apid: int = -1, message_counter: int = 0,
            space_time_ref: int = 0b0000, destination_id: int = 0,
            packet_version: int = 0b000, pus_version: PusVersion = PusVersion.UNKNOWN,
            pus_tm_version: int = 0b0001, ack: int = 0b1111, secondary_header_flag: bool = True,
    ):
        if apid == -1:
            apid = get_tm_apid()
        if pus_version == PusVersion.UNKNOWN:
            pus_version = get_pus_tm_version()
        if time is None:
            time = CdsShortTimestamp.init_from_current_time()
        # packet type for telemetry is 0 as specified in standard
        # specified in standard
        packet_type = PacketTypes.PACKET_TYPE_TM
        self._source_data = source_data
        data_length = self.get_source_data_length(
            timestamp_len=PusTelemetry.PUS_TIMESTAMP_SIZE, pus_version=pus_version
        )
        self.space_packet_header = SpacePacketHeader(
            apid=apid, packet_type=packet_type, secondary_header_flag=secondary_header_flag,
            packet_version=packet_version, data_length=data_length, source_sequence_count=ssc
        )
        self.secondary_packet_header = PusTmSecondaryHeader(
            pus_version=pus_version, service_id=service_id, subservice_id=subservice_id,
            message_counter=message_counter, destination_id=destination_id,
            spacecraft_time_ref=space_time_ref, time=time
        )
        self._valid = False
        self.print_info = ''

    @classmethod
    def __empty(cls, pus_version: PusVersion = PusVersion.UNKNOWN) -> PusTelemetry:
        return PusTelemetry(
            service_id=0, subservice_id=0, time=CdsShortTimestamp.init_from_current_time()
        )

    def pack(self) -> bytearray:
        """
        Serializes the PUS telemetry into a raw packet.
        """
        tm_packet_raw = bytearray()
        # PUS Header
        tm_packet_raw.extend(self.space_packet_header.pack())
        # PUS Source Data Field
        tm_packet_raw.extend(self.secondary_packet_header.pack())
        # Source Data
        tm_packet_raw.extend(self._source_data)
        # CRC16 checksum
        crc_func = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0xffff, xorOut=0x0000)
        crc16 = crc_func(tm_packet_raw)
        tm_packet_raw.append((crc16 & 0xff00) >> 8)
        tm_packet_raw.append(crc16 & 0xff)
        return tm_packet_raw

    @classmethod
    def unpack(
            cls, raw_telemetry: bytearray, pus_version: PusVersion = PusVersion.UNKNOWN
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
        pus_tm.space_packet_header = SpacePacketHeader.unpack(space_packet_raw=raw_telemetry)
        expected_packet_len = get_total_space_packet_len_from_len_field(
            pus_tm.space_packet_header.data_length
        )
        if expected_packet_len > len(raw_telemetry):
            logger = get_console_logger()
            logger.warning(
                f'PusTelemetry: Passed packet with length {len(raw_telemetry)} '
                f'shorter than specified packet length in PUS header {expected_packet_len}'
            )
            raise ValueError
        pus_tm.secondary_packet_header = PusTmSecondaryHeader.unpack(
            header_start=raw_telemetry[SPACE_PACKET_HEADER_SIZE:],
            pus_version=pus_version
        )
        if len(raw_telemetry) - 2 < \
                pus_tm.secondary_packet_header.get_header_size() + SPACE_PACKET_HEADER_SIZE:
            logger = get_console_logger()
            logger.warning("Passed packet too short!")
            raise ValueError
        if pus_tm.get_packet_size() != len(raw_telemetry):
            logger = get_console_logger()
            logger.warning(
                f'PusTelemetry: Packet length field '
                f'{pus_tm.space_packet_header.data_length} might be invalid!'
            )
            logger.warning(f'self.get_packet_size: {pus_tm.get_packet_size()}')
            logger.warning(f'len(raw_telemetry): {len(raw_telemetry)}')
        pus_tm._source_data = raw_telemetry[
            pus_tm.secondary_packet_header.get_header_size() + SPACE_PACKET_HEADER_SIZE:-2
        ]
        pus_tm._crc = \
            raw_telemetry[len(raw_telemetry) - 2] << 8 | raw_telemetry[len(raw_telemetry) - 1]
        pus_tm.print_info = ""
        pus_tm.__perform_crc_check(raw_telemetry)
        return pus_tm

    def __str__(self):
        return f"PUS TM[{self.secondary_packet_header.service_id}," \
               f"{self.secondary_packet_header.subservice_id}] with message counter " \
               f"{self.secondary_packet_header.message_counter}"

    def __repr__(self):
        return f"{self.__class__.__name__}(service={self.secondary_packet_header.service_id!r}, " \
               f"subservice={self.secondary_packet_header.subservice_id!r})"

    def get_service(self):
        """
        :return: Service ID
        """
        return self.secondary_packet_header.service_id

    def get_subservice(self):
        """
        :return: Subservice ID
        """
        return self.secondary_packet_header.subservice_id

    def is_valid(self):
        return self._valid

    def get_tm_data(self) -> bytearray:
        """
        :return: TM application data (raw)
        """
        return self._source_data

    def get_packet_id(self):
        return self.space_packet_header.packet_id

    def __perform_crc_check(self, raw_telemetry: bytearray) -> bool:
        crc_func = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0xFFFF, xorOut=0x0000)
        if len(raw_telemetry) < self.get_packet_size():
            logger = get_console_logger()
            logger.warning('Invalid packet length')
            return False
        data_to_check = raw_telemetry[0:self.get_packet_size()]
        crc = crc_func(data_to_check)
        if crc == 0:
            self._valid = True
            return True
        else:
            logger = get_console_logger()
            logger.warning('Invalid CRC detected !')
            return False

    def get_source_data_length(self, timestamp_len: int, pus_version: PusVersion) -> int:
        """Retrieve size of TM packet data header in bytes.

        Formula according to PUS Standard: C = (Number of octets in packet source data field) - 1.
        The size of the TM packet is the size of the packet secondary header with
        the timestamp + the length of the application data + PUS timestamp size +
        length of the CRC16 checksum - 1
        """
        try:
            if pus_version == PusVersion.PUS_A:
                data_length = \
                    PusTmSecondaryHeader.HEADER_SIZE_WITHOUT_TIME_PUS_A + \
                    timestamp_len + len(self._source_data) + 1
            else:
                data_length = \
                    PusTmSecondaryHeader.HEADER_SIZE_WITHOUT_TIME_PUS_C + \
                    timestamp_len + len(self._source_data) + 1
            return data_length
        except TypeError:
            print("PusTelecommand: Invalid type of application data!")
            return 0

    def specify_packet_info(self, print_info: str):
        """Caches a print information string for later printing
        :param print_info:
        :return:
        """
        self.print_info = print_info

    def append_packet_info(self, print_info: str):
        """Similar to the function above, but appends to the existing information string.
        :param print_info:
        :return:
        """
        self.print_info = self.print_info + print_info

    def append_telemetry_content(self, content_list: list):
        """Default implementation adds the PUS header content to the list which can then be
        printed with a simple print() command. To add additional content, override this method
        (don't forget to still call this function with super() if the header is required)
        :param content_list: Header content will be appended to this list
        :return:
        """
        self.secondary_packet_header.append_data_field_header(content_list=content_list)
        self.space_packet_header.append_space_packet_header_content(content_list=content_list)
        if self.is_valid():
            content_list.append("Yes")
        else:
            content_list.append("No")

    def append_telemetry_column_headers(self, header_list: list):
        """Default implementation adds the PUS header content header (confusing, I know)
        to the list which can then be  printed with a simple print() command.
        To add additional headers, override this method
        (don't forget to still call this function with super() if the header is required)
        :param header_list: Header content will be appended to this list
        :return:
        """
        self.secondary_packet_header.append_data_field_header_column_header(header_list=header_list)
        self.space_packet_header.append_space_packet_header_column_headers(header_list=header_list)
        header_list.append("Packet valid")

    def get_custom_printout(self) -> str:
        """Can be used to supply any additional custom printout.
        :return: String which will be printed by TmTcPrinter class as well as logged if specified
        """
        return ""

    def get_packet_size(self) -> int:
        """
        :return: Size of the TM packet based on the space packet header data length field.
        The space packet data field is the full length of data field minus one without the space packet header.
        """
        return SPACE_PACKET_HEADER_SIZE + self.space_packet_header.data_length + 1

    def get_apid(self) -> int:
        return self.space_packet_header.apid

    def get_ssc(self) -> int:
        """Get the source sequence count
        :return: Source Sequence Count (see below, or PUS documentation)
        """
        return self.space_packet_header.ssc

    def return_full_packet_string(self):
        packet_raw = self.pack()
        return get_printable_data_string(packet_raw, len(packet_raw))

    def print_full_packet_string(self):
        """Print the full TM packet in a clean format."""
        packet_raw = self.pack()
        print(get_printable_data_string(packet_raw, len(packet_raw)))

    def print_source_data(self):
        """Prints the TM source data in a clean format
        :return:
        """
        print(get_printable_data_string(self._source_data, len(self._source_data)))

    def return_source_data_string(self):
        """Returns the source data string"""
        return get_printable_data_string(self._source_data, len(self._source_data))


class PusTmSecondaryHeader:
    """Unpacks the PUS telemetry packet secondary header.

    Currently only supports CDS short timestamps"""
    HEADER_SIZE_WITHOUT_TIME_PUS_A = 4
    HEADER_SIZE_WITHOUT_TIME_PUS_C = 7

    def __init__(
            self, pus_version: PusVersion, service_id: int, subservice_id: int,
            time: CdsShortTimestamp, message_counter: int, destination_id: int = 0,
            spacecraft_time_ref: int = 0,
    ):
        """Create a PUS telemetry secondary header object.

        :param pus_version:
        :param service_id:
        :param subservice_id:
        :param message_counter: 8 bit counter for PUS A, 16 bit counter for PUS C
        :param spacecraft_time_ref: Space time reference if PUS C is used
        :param time: Time field
        """
        self.pus_version = pus_version
        self.spacecraft_time_ref = spacecraft_time_ref
        if self.pus_version == PusVersion.PUS_A:
            self.pus_version_number = 0
        else:
            self.pus_version_number = 1
        self.service_id = service_id
        self.subservice_id = subservice_id
        if (self.pus_version == PusVersion.PUS_A and message_counter > 255) or \
                (self.pus_version == PusVersion.PUS_C and message_counter > 65536):
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
            message_counter=0
        )

    def pack(self) -> bytearray:
        secondary_header = bytearray()
        if self.pus_version == PusVersion.PUS_A:
            secondary_header.append((self.pus_version_number & 0x07) << 4)
        elif self.pus_version == PusVersion.PUS_C:
            secondary_header.append(self.pus_version_number << 4 | self.spacecraft_time_ref)
        secondary_header.append(self.service_id)
        secondary_header.append(self.subservice_id)
        if self.pus_version == PusVersion.PUS_A:
            secondary_header.append(self.message_counter)
        elif self.pus_version == PusVersion.PUS_C:
            secondary_header.append((self.message_counter & 0xff00) >> 8)
            secondary_header.append(self.message_counter & 0xff)
            secondary_header.append((self.destination_id & 0xff00) >> 8)
            secondary_header.append(self.destination_id & 0xff)
        secondary_header.extend(self.time.pack())
        return secondary_header

    @classmethod
    def unpack(cls, header_start: bytearray, pus_version: PusVersion) -> PusTmSecondaryHeader:
        """Unpack the PUS TM secondary header from the raw packet starting at the header index.
        The user still needs to specify the PUS version because the version field is parsed
        differently depending on the PUS version.

        :param header_start:
        :param pus_version:
        :raises ValueError: bytearray too short or PUS version missmatch.
        :return:
        """
        if pus_version == PusVersion.UNKNOWN:
            pus_version = get_pus_tm_version()
        secondary_header = cls.__empty()
        current_idx = 0
        if pus_version == PusVersion.PUS_A:
            secondary_header.pus_version = PusVersion.PUS_A
            secondary_header.pus_version_number = (header_start[current_idx] & 0x70) >> 4
            if secondary_header.pus_version_number == 1:
                logger = get_console_logger()
                logger.warning(
                    'PUS version field value 1 found where PUS A value (0) was expected!'
                )
                raise ValueError

        elif pus_version == PusVersion.PUS_C:
            secondary_header.pus_version = PusVersion.PUS_C
            if secondary_header.pus_version_number == 0:
                logger = get_console_logger()
                logger.warning(
                    'PUS version field value 0 found where PUS C value (1) was expected!'
                )
                raise ValueError
            secondary_header.pus_version_number = (header_start[current_idx] & 0xF0) >> 4
            secondary_header.spacecraft_time_ref = header_start[current_idx] & 0x0F
        if len(header_start) < secondary_header.get_header_size():
            logger = get_console_logger()
            logger.warning(
                f'Invalid PUS data field header size, '
                f'less than expected {secondary_header.get_header_size()} bytes'
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
            secondary_header.message_counter = \
                header_start[current_idx] << 8 | header_start[current_idx + 1]
            current_idx += 2
        if pus_version == PusVersion.PUS_C:
            secondary_header.destination_id = \
                header_start[current_idx] << 8 | header_start[current_idx + 1]
            current_idx += 2
        # If other time formats are supported in the future, this information can be used
        #  to unpack the correct time code
        time_code_id = read_p_field(header_start[current_idx])
        if time_code_id:
            pass
        secondary_header.time = CdsShortTimestamp.unpack(
            time_field=header_start[current_idx: current_idx + PusTelemetry.PUS_TIMESTAMP_SIZE]
        )
        return secondary_header

    def append_data_field_header(self, content_list: list):
        """Append important data field header parameters to the passed content list.
        :param content_list:
        :return:
        """
        content_list.append(str(self.service_id))
        content_list.append(str(self.subservice_id))
        content_list.append(str(self.message_counter))
        self.time.add_time_to_content_list(content_list=content_list)

    def append_data_field_header_column_header(self, header_list: list):
        """Append important data field header column headers to the passed list.
        :param header_list:
        :return:
        """
        header_list.append("Service")
        header_list.append("Subservice")
        header_list.append("Subcounter")
        self.time.add_time_headers_to_header_list(header_list=header_list)

    def get_header_size(self):
        if self.pus_version == PusVersion.PUS_A:
            return PusTelemetry.PUS_TIMESTAMP_SIZE + 4
        else:
            return PusTelemetry.PUS_TIMESTAMP_SIZE + 7


def get_printable_data_string(byte_array: bytearray, length: int) -> str:
    """Returns the TM data in a clean printable string format
    Prints payload data in default mode
    and prints the whole packet if full_packet = True is passed.
    :return:
    """
    str_to_print = "["
    for index in range(length):
        str_to_print += str(hex(byte_array[index])) + " , "
    str_to_print = str_to_print.rstrip()
    str_to_print = str_to_print.rstrip(',')
    str_to_print = str_to_print.rstrip()
    str_to_print += "]"
    return str_to_print


# Structure of a PUS Packet :
# A PUS packet consists of consecutive bits, the allocation and structure is standardised.
# Extended information can be found in ECSS-E-70-41A  on p.46
# The easiest form to send a PUS Packet is in hexadecimal form.
# A two digit hexadecimal number equals one byte, 8 bits or one octet
# o = optional, Srv = Service
#
# The structure is shown as follows for TM[17,2]
# 1. Structure Header
# 2. Structure Subheader
# 3. Component (size in bits)
# 4. Hexadecimal number
# 5. Binary Number
# 6. Decimal Number
#
# Packet Structure for PUS A:
#
# -------------------------------------------Packet Header(48)------------------------------------------|   Packet   |
#  ----------------Packet ID(16)----------------------|Packet Sequence Control (16)| Packet Length (16) | Data Field |
# Version       | Type(1) |Data Field    |APID(11)    | SequenceFlags(2) |Sequence |                    | (Variable) |
# Number(3)     |         |Header Flag(1)|            |                  |Count(14)|                    |            |
#           0x08               |    0x73              |       0xc0       | 0x19    |   0x00  |   0x04   |            |
#    000      0      1      000|  01110011            | 11  000000       | 00011001|00000000 | 0000100  |            |
#     0   |   0   |  1     |    115(ASCII s)          | 3 |            25          |   0     |    4     |            |
#
#   - Packet Length is an unsigned integer C = Number of Octets in Packet Data Field - 1
#
# Packet Data Field Structure:
#
# ------------------------------------------------Packet Data Field------------------------------------------------- |
# ---------------------------------Data Field Header --------------------------------------|AppData|Spare|PacketErrCtr |
# Spare(1)|TM PUS Ver.(3)|Spare(4)|SrvType (8)|SrvSubtype(8)|Subcounter(8)|Time(7)|Spare(o)|(var)  |(var)|  (16)       |
#        0x11 (0x1F)              |  0x11     |   0x01      |             |       |        |       |     |     Calc.   |
#    0     001     0000           |00010001   | 00000001    |             |       |        |       |     |             |
#    0      1       0             |    17     |     2       |             |       |        |       |     |             |
#
# - Thus subcounter is specified optional for PUS A, but for this implementation it is expected the subcounter
#   is contained in the raw packet
# - In PUS A, the destination ID can be present as one byte in the spare field. It was omitted for the FSFW
# - In PUS C, the last spare bits of the first byte are replaced by the space time reference field
# - PUS A and PUS C both use the CDS short seven byte timestamp in the time field
# - PUS C has a 16 bit counter sequence counter and a 16 bit destination ID before the time field
