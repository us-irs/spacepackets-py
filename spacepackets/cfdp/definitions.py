import enum
import struct


class PduType(enum.IntEnum):
    FILE_DIRECTIVE = 0
    FILE_DATA = 1


class Direction(enum.IntEnum):
    TOWARDS_RECEIVER = 0
    TOWARDS_SENDER = 1


class TransmissionModes(enum.IntEnum):
    ACKNOWLEDGED = 0
    UNACKNOWLEDGED = 1


class CrcFlag(enum.IntEnum):
    NO_CRC = 0
    WITH_CRC = 1
    GLOBAL_CONFIG = 2


class SegmentMetadataFlag(enum.IntEnum):
    """Aways 0 and ignored for File Directive PDUs (CCSDS 727.0-B-5 p.75)"""
    NOT_PRESENT = 0
    PRESENT = 1


class SegmentationControl(enum.IntEnum):
    """Always 0 and ignored for File Directive PDUs (CCSDS 727.0-B-5 p.75)"""
    NO_RECORD_BOUNDARIES_PRESERVATION = 0
    RECORD_BOUNDARIES_PRESERVATION = 1


class LenInBytes(enum.IntEnum):
    ONE_BYTE = 1
    TWO_BYTES = 2
    FOUR_BYTES = 4
    EIGHT_BYTES = 8
    GLOBAL = 90
    NONE = 99


def get_transaction_seq_num_as_bytes(
        transaction_seq_num: int, byte_length: LenInBytes
) -> bytearray:
    """Return the byte representation of the transaction sequece number
    :param transaction_seq_num:
    :param byte_length:
    :raises ValueError: Invalid input
    :return:
    """
    if byte_length == LenInBytes.ONE_BYTE and transaction_seq_num < 255:
        return bytearray([transaction_seq_num])
    if byte_length == LenInBytes.TWO_BYTES and transaction_seq_num < pow(2, 16) - 1:
        return bytearray(struct.pack('!H', transaction_seq_num))
    if byte_length == LenInBytes.FOUR_BYTES and transaction_seq_num < pow(2, 32) - 1:
        return bytearray(struct.pack('!I', transaction_seq_num))
    if byte_length == LenInBytes.EIGHT_BYTES and transaction_seq_num < pow(2, 64) - 1:
        return bytearray(struct.pack('!Q', transaction_seq_num))
    raise ValueError


# File sizes, determine the field sizes of FSS fields
class FileSize(enum.IntEnum):
    # 32 bit maximum file size and FSS size
    NORMAL = 0
    # 64 bit maximum file size and FSS size
    LARGE = 1
    GLOBAL_CONFIG = 2


# Checksum types according to the SANA Checksum Types registry
# https://sanaregistry.org/r/checksum_identifiers/
class ChecksumTypes(enum.IntEnum):
    # Modular legacy checksum
    MODULAR = 0
    CRC_32_PROXIMITY_1 = 1
    CRC_32C = 2
    CRC_32 = 3
    NULL_CHECKSUM = 15
