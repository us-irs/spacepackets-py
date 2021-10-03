"""This module contains the PUS telecommand class representation to pack telecommands.
"""
from __future__ import annotations
import sys
from typing import Tuple

from spacepackets.log import get_console_logger
from spacepackets.ccsds.spacepacket import \
    SpacePacketHeader, \
    PacketTypes, \
    SPACE_PACKET_HEADER_SIZE
from spacepackets.ecss.conf import get_default_apid, PusVersion, get_pus_tc_version


try:
    from crcmod.predefined import mkPredefinedCrcFun
except ImportError:
    print("crcmod package not installed!")
    sys.exit(1)


class PusTcDataFieldHeader:
    def __init__(
            self, service_type: int, service_subtype: int, source_id: int = 0,
            pus_tc_version: PusVersion = PusVersion.PUS_C, ack_flags: int = 0b1111,
            secondary_header_flag: int = 0
    ):
        self.service_type = service_type
        self.service_subtype = service_subtype
        self.source_id = source_id
        self.pus_tc_version = pus_tc_version
        self.ack_flags = ack_flags
        if self.pus_tc_version == PusVersion.PUS_A:
            pus_version_num = 1
            self.pus_version_and_ack_byte = \
                secondary_header_flag << 7 | pus_version_num << 4 | ack_flags
        else:
            pus_version_num = 2
            self.pus_version_and_ack_byte = pus_version_num << 4 | ack_flags

    def pack(self) -> bytearray:
        header_raw = bytearray()
        header_raw.append(self.pus_version_and_ack_byte)
        header_raw.append(self.service_type)
        header_raw.append(self.service_subtype)
        if self.pus_tc_version == PusVersion.PUS_C:
            header_raw.append(self.source_id << 8 & 0xff)
            header_raw.append(self.source_id & 0xff)
        else:
            # PUS A includes optional source ID field as well
            header_raw.append(self.source_id)
        return header_raw

    @classmethod
    def unpack(
            cls, raw_packet: bytes, pus_version: PusVersion = PusVersion.PUS_C
    ) -> PusTcDataFieldHeader:
        min_expected_len = cls.get_header_size(pus_version=pus_version)
        if len(raw_packet) < min_expected_len:
            logger = get_console_logger()
            logger.warning(
                f'Passed bytearray too short, expected minimum length {min_expected_len}'
            )
            raise ValueError
        version_and_ack_byte = raw_packet[0]
        secondary_header_flag = 0
        if pus_version == PusVersion.PUS_C:
            pus_tc_version = (version_and_ack_byte & 0xf0) >> 4
            if pus_tc_version != PusVersion.PUS_C:
                logger = get_console_logger()
                logger.warning(
                    f'PUS C expected but TC version field missmatch detected. '
                    f'Expected {PusVersion.PUS_C}, got {pus_tc_version}'
                )
                raise ValueError
        elif pus_version == PusVersion.PUS_A:
            if pus_version != PusVersion.PUS_A:
                logger = get_console_logger()
                logger.warning(
                    f'PUS A expected but TC version field missmatch detected. '
                    f'Expected {PusVersion.PUS_A}, got {pus_version}'
                )
                raise ValueError
            secondary_header_flag = (version_and_ack_byte & 0x80) >> 7
        ack_flags = version_and_ack_byte & 0x0f
        service = raw_packet[1]
        subservice = raw_packet[2]
        if pus_version == PusVersion.PUS_C:
            source_id = raw_packet[3] << 8 | raw_packet[4]
        else:
            source_id = raw_packet[3]
        return cls(
            service_type=service,
            service_subtype=subservice,
            secondary_header_flag=secondary_header_flag,
            ack_flags=ack_flags,
            source_id=source_id,
            pus_tc_version=pus_version
        )

    @staticmethod
    def get_header_size(pus_version: PusVersion):
        if pus_version == PusVersion.PUS_A:
            return 4
        elif pus_version == PusVersion.PUS_C:
            return 5


# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-arguments
class PusTelecommand:
    """Class representation of a PUS telecommand. It can be used to pack a raw telecommand from
    input parameters. The structure of a PUS telecommand is specified in ECSS-E-70-41A on p.42
    and is also shown below (bottom)
    """

    def __init__(
            self, service: int, subservice: int, ssc=0,
            app_data: bytearray = bytearray([]), source_id: int = 0,
            pus_tc_version: PusVersion = PusVersion.PUS_C, ack_flags: int = 0b1111, apid: int = -1
    ):
        """Initiate a PUS telecommand from the given parameters. The raw byte representation
        can then be retrieved with the :py:meth:`pack` function.

        :param service: PUS service number
        :param subservice: PUS subservice number
        :param apid: Application Process ID as specified by CCSDS
        :param ssc: Source Sequence Count. Application should take care of incrementing this.
            Limited to 2 to the power of 14 by the number of bits in the header
        :param app_data: Application data in the Packet Data Field
        :param source_id: Source ID will be supplied as well. Can be used to distinguish
            different packet sources (e.g. different ground stations)
        :param pus_tc_version:  PUS TC version. 1 for ECSS-E-70-41A
        :raises ValueError: Invalid input parameters
        """
        if apid == -1:
            apid = get_default_apid()
        if pus_tc_version == PusVersion.GLOBAL_CONFIG:
            pus_tc_version = get_pus_tc_version()
        packet_type = PacketTypes.PACKET_TYPE_TC
        secondary_header_flag = 1
        logger = get_console_logger()
        if subservice > 255:
            logger.warning("Subservice value invalid. Setting to 0")
            subservice = 0
        if service > 255:
            logger.warning("Service value invalid. Setting to 0")
            service = 0
        # SSC can have maximum of 14 bits
        if ssc > pow(2, 14):
            logger.warning("SSC invalid, setting to 0")
            ssc = 0
        self.data_field_header = PusTcDataFieldHeader(
            service_type=service, service_subtype=subservice, ack_flags=ack_flags,
            source_id=source_id, pus_tc_version=pus_tc_version
        )
        data_length = self.get_data_length(
            secondary_header_len=self.data_field_header.get_header_size(pus_version=pus_tc_version),
            app_data_len=len(app_data),
        )
        self.space_packet_header = SpacePacketHeader(
            apid=apid, secondary_header_flag=bool(secondary_header_flag), packet_type=packet_type,
            data_length=data_length, source_sequence_count=ssc
        )
        self._app_data = app_data
        self._valid = True
        self.crc = 0

    def __repr__(self):
        """Returns the representation of a class instance."""
        return f"{self.__class__.__name__}(service={self.data_field_header.service_type!r}, " \
               f"subservice={self.data_field_header.service_subtype!r}, " \
               f"ssc={self.space_packet_header.ssc!r}, apid={self.get_apid()})"

    def __str__(self):
        """Returns string representation of a class instance."""
        return f"TC[{self.data_field_header.service_type}, " \
               f"{self.data_field_header.service_subtype}] with SSC {self.space_packet_header.ssc}"

    def is_valid(self):
        return self._is_valid

    def get_total_length(self) -> int:
        """Length of full packet in bytes.
        The header length is 6 bytes and the data length + 1 is the size of the data field.
        """
        secondary_header_len = self.data_field_header.get_header_size(
            pus_version=self.data_field_header.pus_tc_version
        )
        return self.get_data_length(
            secondary_header_len=secondary_header_len,
            app_data_len=len(self._app_data)
        ) + SPACE_PACKET_HEADER_SIZE + 1

    @classmethod
    def __empty(cls):
        return cls(
            service=0,
            subservice=0,
            apid=0,
            ssc=0,
            app_data=bytearray()
        )

    def pack(self) -> bytearray:
        """Serializes the TC data fields into a bytearray."""
        packed_data = bytearray()
        packed_data.extend(self.space_packet_header.pack())
        packed_data.extend(self.data_field_header.pack())
        packed_data += self.get_app_data()
        crc_func = mkPredefinedCrcFun(crc_name='crc-ccitt-false')
        self.crc = crc_func(packed_data)
        self._valid = True
        packed_data.append((self.crc & 0xff00) >> 8)
        packed_data.append(self.crc & 0xff)
        return packed_data

    @classmethod
    def unpack(cls, raw_packet: bytes, pus_version: PusVersion) -> PusTelecommand:
        tc_unpacked = cls.__empty()
        tc_unpacked._space_packet_header.unpack(space_packet_raw=raw_packet)
        tc_unpacked._data_field_header.unpack(raw_packet=raw_packet, pus_version=pus_version)
        header_len = \
            SPACE_PACKET_HEADER_SIZE + \
            tc_unpacked._data_field_header.get_header_size(pus_version=pus_version)
        expected_packet_len = tc_unpacked.get_packet_size()
        if len(raw_packet) < expected_packet_len:
            logger = get_console_logger()
            logger.warning(
                f'Invalid length of raw telecomamnd packet, expected minimum length '
                f'{expected_packet_len}'
            )
        tc_unpacked.app_data = raw_packet[header_len:expected_packet_len - 2]
        tc_unpacked.crc = raw_packet[expected_packet_len - 2: expected_packet_len]
        crc_func = mkPredefinedCrcFun(crc_name='crc-ccitt-false')
        whole_packet = raw_packet[:expected_packet_len]
        should_be_zero = crc_func(whole_packet)
        if should_be_zero == 0:
            tc_unpacked._valid = True
        else:
            logger = get_console_logger()
            logger.warning('Invalid CRC16 in raw telecommand detected')
            tc_unpacked._valid = False

    def get_packet_size(self) -> int:
        """Retrieve the full packet size when packed
        :return: Size of the TM packet based on the space packet header data length field.
        The space packet data field is the full length of data field minus one without
        the space packet header.
        """
        return self.space_packet_header.get_packet_size()

    @staticmethod
    def get_data_length(app_data_len: int, secondary_header_len: int) -> int:
        """Retrieve size of TC packet in bytes.
        Formula according to PUS Standard: C = (Number of octets in packet data field) - 1.
        The size of the TC packet is the size of the packet secondary header with
        source ID + the length of the application data + length of the CRC16 checksum - 1
        """
        try:
            data_length = secondary_header_len + app_data_len + 1
            return data_length
        except TypeError:
            logger = get_console_logger()
            logger.warning("PusTelecommand: Invalid type of application data!")
            return 0

    def pack_command_tuple(self) -> Tuple[bytearray, PusTelecommand]:
        """Pack a tuple consisting of the raw packet as the first entry and the class representation
        as the second entry
        """
        command_tuple = (self.pack(), self)
        return command_tuple

    def get_service(self) -> int:
        return self.data_field_header.service_type

    def get_subservice(self) -> int:
        return self.data_field_header.service_subtype

    def get_ssc(self) -> int:
        return self.space_packet_header.ssc

    def get_apid(self) -> int:
        return self.space_packet_header.apid

    def get_packet_id(self) -> int:
        return self.space_packet_header.packet_id

    def get_app_data(self) -> bytearray:
        return self._app_data

    def print(self):
        """Print the raw command in a clean format.
        """
        packet = self.pack()
        print("Command in Hexadecimal: [", end="")
        for counter in range(len(packet)):
            if counter == len(packet) - 1:
                print(str(hex(packet[counter])), end="")
            else:
                print(str(hex(packet[counter])) + ", ", end="")
        print("]")


def generate_packet_crc(tc_packet: bytearray) -> bytearray:
    """Removes current Packet Error Control, calculates new
    CRC16 checksum and adds it as correct Packet Error Control Code.
    Reference: ECSS-E70-41A p. 207-212
    """
    crc_func = mkPredefinedCrcFun(crc_name='crc-ccitt-false')
    crc = crc_func(bytearray(tc_packet[0:len(tc_packet) - 2]))
    tc_packet[len(tc_packet) - 2] = (crc & 0xFF00) >> 8
    tc_packet[len(tc_packet) - 1] = crc & 0xFF
    return tc_packet


def generate_crc(data: bytearray) -> bytearray:
    """Takes the application data, appends the CRC16 checksum and returns resulting bytearray
    """
    data_with_crc = bytearray()
    data_with_crc += data
    crc_func = mkPredefinedCrcFun(crc_name='crc-ccitt-false')
    crc = crc_func(data)
    data_with_crc.append((crc & 0xFF00) >> 8)
    data_with_crc.append(crc & 0xFF)
    return data_with_crc
