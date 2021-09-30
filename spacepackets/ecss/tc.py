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
    import crcmod
except ImportError:
    print("crcmod package not installed!")
    sys.exit(1)


class PusTcDataFieldHeaderSerialize:
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

    def get_header_size(self):
        if self.pus_tc_version == PusVersion.PUS_A:
            return 4
        elif self.pus_tc_version == PusVersion.PUS_C:
            return 5


# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-arguments
class PusTelecommand:
    """Class representation of a PUS telecommand. It can be used to pack a raw telecommand from
    input parameters. The structure of a PUS telecommand is specified in ECSS-E-70-41A on p.42
    and is also shown below (bottom)
    """
    # This is the current size of a telecommand without application data. Consists of
    # the 6 byte packet header, 4 byte data field header (1 byte source ID) and 2 byte CRC.
    CURRENT_NON_APP_DATA_SIZE = 10

    def __init__(
            self, service: int, subservice: int, ssc=0,
            app_data: bytearray = bytearray([]), source_id: int = 0,
            pus_tc_version: int = PusVersion.UNKNOWN, ack_flags: int = 0b1111, apid: int = -1
    ):
        """Initiate a PUS telecommand from the given parameters. The raw byte representation
        can then be retrieved with the pack() function.

        :param service: PUS service number
        :param subservice: PUS subservice number
        :param apid: Application Process ID as specified by CCSDS
        :param ssc: Source Sequence Count. Application should take care of incrementing this.
            Limited to 2 to the power of 14 by the number of bits in the header
        :param app_data: Application data in the Packet Data Field
        :param source_id: Source ID will be supplied as well. Can be used to distinguish
            different packet sources (e.g. different ground stations)
        :param pus_tc_version:  PUS TC version. 1 for ECSS-E-70-41A

        """
        if apid == -1:
            apid = get_default_apid()
        self.apid = apid
        if pus_tc_version == PusVersion.UNKNOWN:
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
        self._data_field_header = PusTcDataFieldHeaderSerialize(
            service_type=service, service_subtype=subservice, ack_flags=ack_flags,
            source_id=source_id, pus_tc_version=pus_tc_version
        )
        data_length = self.get_data_length(
            secondary_header_len=self._data_field_header.get_header_size(),
            app_data_len=len(app_data),
        )
        self._space_packet_header = SpacePacketHeader(
            apid=apid, secondary_header_flag=bool(secondary_header_flag), packet_type=packet_type,
            data_length=data_length, source_sequence_count=ssc
        )
        self.app_data = app_data
        self.packed_data = bytearray()

    def __repr__(self):
        """Returns the representation of a class instance."""
        return f"{self.__class__.__name__}(service={self._data_field_header.service_type!r}, " \
               f"subservice={self._data_field_header.service_subtype!r}, " \
               f"ssc={self._space_packet_header.ssc!r}, apid={self.apid})"

    def __str__(self):
        """Returns string representation of a class instance."""
        return f"TC[{self._data_field_header.service_type}, " \
               f"{self._data_field_header.service_subtype}] with SSC {self._space_packet_header.ssc}"

    def get_total_length(self):
        """Length of full packet in bytes.
        The header length is 6 bytes and the data length + 1 is the size of the data field.
        """
        return self.get_data_length(
            secondary_header_len=self._data_field_header.get_header_size(),
            app_data_len=len(self.app_data)
        ) + SPACE_PACKET_HEADER_SIZE + 1

    def pack(self) -> bytearray:
        """Serializes the TC data fields into a bytearray."""
        self.packed_data = bytearray()
        self.packed_data.extend(self._space_packet_header.pack())
        self.packed_data.extend(self._data_field_header.pack())
        self.packed_data += self.app_data
        crc_func = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0xFFFF, xorOut=0x0000)
        crc = crc_func(self.packed_data)

        self.packed_data.append((crc & 0xFF00) >> 8)
        self.packed_data.append(crc & 0xFF)
        return self.packed_data

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

    def get_service(self):
        return self._data_field_header.service_type

    def get_subservice(self):
        return self._data_field_header.service_subtype

    def get_ssc(self):
        return self._space_packet_header.ssc

    def get_apid(self):
        return self._space_packet_header.apid

    def get_packet_id(self):
        return self._space_packet_header.packet_id

    def get_app_data(self):
        return self.app_data

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
    crc_func = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0xFFFF, xorOut=0x0000)
    crc = crc_func(bytearray(tc_packet[0:len(tc_packet) - 2]))
    tc_packet[len(tc_packet) - 2] = (crc & 0xFF00) >> 8
    tc_packet[len(tc_packet) - 1] = crc & 0xFF
    return tc_packet


def generate_crc(data: bytearray) -> bytearray:
    """Takes the application data, appends the CRC16 checksum and returns resulting bytearray
    """
    data_with_crc = bytearray()
    data_with_crc += data
    crc_func = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0xFFFF, xorOut=0x0000)
    crc = crc_func(data)
    data_with_crc.append((crc & 0xFF00) >> 8)
    data_with_crc.append(crc & 0xFF)
    return data_with_crc


# pylint: disable=line-too-long

# Structure of a PUS TC Packet :
# A PUS wiretapping_packet consists of consecutive bits, the allocation and structure is
# standardised. Extended information can be found in ECSS-E-70-41A  on p.42
# The easiest form to send a PUS Packet is in hexadecimal form.
# A two digit hexadecimal number equals one byte, 8 bits or one octet
# o = optional, Srv = Service
#
# The structure is shown as follows for TC[17,1]
# 1. Structure Header
# 2. Structure Subheader
# 3. Component (size in bits)
# 4. Hexadecimal number
# 5. Binary Number
# 6. Decimal Number
#
# -------------------------------------------Packet Header(48)------------------------------------------|   Packet   |
#  ----------------Packet ID(16)----------------------|Packet Sequence Control (16)| Packet Length (16) | Data Field |
# Version       | Type(1) |Data Field    |APID(11)    | SequenceFlags(2) |Sequence |                    | (Variable) |
# Number(3)     |         |Header Flag(1)|            |                  |Count(14)|                    |            |
#           0x18               |    0x73              |       0xc0       | 0x19    |   0x00  |   0x04   |            |
#    000      1      1      000|  01110011            | 11  000000       | 00011001|00000000 | 0000100  |            |
#     0   |   1   |  1     |    115(ASCII s)          | 3 |            25          |   0     |    4     |            |
#
#   - Packet Length is an unsigned integer C = Number of Octets in Packet Data Field - 1
#
# Packet Data Field Structure:
#
# ------------------------------------------------Packet Data Field------------------------------------------------- |
# ---------------------------------Data Field Header ---------------------------|AppData|Spare|    PacketErrCtr      |
# CCSDS(1)|TC PUS Ver.(3)|Ack(4)|SrvType (8)|SrvSubtype(8)|Source ID(o)|Spare(o)|  (var)|(var)|         (16)         |
#        0x11 (0x1F)            |  0x11     |   0x01      |            |        |       |     | 0xA0     |    0xB8   |
#    0     001     1111         |00010001   | 00000001    |            |        |       |     |          |           |
#    0      1       1111        |    17     |     1       |            |        |       |     |          |           |
#
#   - The source ID is present as one byte. For now, ground = 0x00.
