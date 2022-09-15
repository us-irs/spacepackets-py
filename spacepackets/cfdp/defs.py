from __future__ import annotations
import enum


CFDP_VERSION_2_NAME = "CCSDS 727.0-B-5"
# Second version of the protocol, only this one is supported here
CFDP_VERSION_2 = 0b001


class UnsupportedCfdpVersion(Exception):
    def __init__(self, version: int):
        self.version = version

    def __str__(self):
        return f"Unsupported CFDP version {self.version}"


class PduType(enum.IntEnum):
    FILE_DIRECTIVE = 0
    FILE_DATA = 1


class Direction(enum.IntEnum):
    """This is used for PDU forwarding"""

    TOWARDS_RECEIVER = 0
    TOWARDS_SENDER = 1


class TransmissionMode(enum.IntEnum):
    ACKNOWLEDGED = 0
    UNACKNOWLEDGED = 1


class CrcFlag(enum.IntEnum):
    NO_CRC = 0
    WITH_CRC = 1


class SegmentMetadataFlag(enum.IntEnum):
    """Aways 0 and ignored for File Directive PDUs (CCSDS 727.0-B-5 p.75)"""

    NOT_PRESENT = 0
    PRESENT = 1


class SegmentationControl(enum.IntEnum):
    """Always 0 and ignored for File Directive PDUs (CCSDS 727.0-B-5 p.75)"""

    NO_RECORD_BOUNDARIES_PRESERVATION = 0
    RECORD_BOUNDARIES_PRESERVATION = 1


class FaultHandlerCode(enum.IntEnum):
    NOTICE_OF_CANCELLATION = 0b0001
    NOTICE_OF_SUSPENSION = 0b0010
    IGNORE_ERROR = 0b0011
    ABANDON_TRANSACTION = 0b0100


class LenInBytes(enum.IntEnum):
    ZERO_OR_NONE = 0
    ONE_BYTE = 1
    TWO_BYTES = 2
    FOUR_BYTES = 4
    EIGHT_BYTES = 8


class ConditionCode(enum.IntEnum):
    NO_CONDITION_FIELD = -1
    # As expected, this is not an error condition for which a fault handler override can be
    # specified
    NO_ERROR = 0b0000
    POSITIVE_ACK_LIMIT_REACHED = 0b0001
    KEEP_ALIVE_LIMIT_REACHED = 0b0010
    INVALID_TRANSMISSION_MODE = 0b0011
    FILESTORE_REJECTION = 0b0100
    FILE_CHECKSUM_FAILURE = 0b0101
    FILE_SIZE_ERROR = 0b0110
    NAK_LIMIT_REACHED = 0b0111
    INACTIVITY_DETECTED = 0b1000
    CHECK_LIMIT_REACHED = 0b1010
    UNSUPPORTED_CHECKSUM_TYPE = 0b1011
    # The following two are not actual fault conditions for which fault handler overrides
    # can be specified
    SUSPEND_REQUEST_RECEIVED = 0b1110
    CANCEL_REQUEST_RECEIVED = 0b1111


# File sizes, determine the field sizes of FSS fields
class LargeFileFlag(enum.IntEnum):
    # 32 bit maximum file size and FSS size
    NORMAL = 0
    # 64 bit maximum file size and FSS size
    LARGE = 1


# Checksum types according to the SANA Checksum Types registry
# https://sanaregistry.org/r/checksum_identifiers/
class ChecksumType(enum.IntEnum):
    # Modular legacy checksum
    MODULAR = 0
    CRC_32_PROXIMITY_1 = 1
    CRC_32C = 2
    # Polynomial: 0x4C11DB7. This is the preferred checksum for now.
    CRC_32 = 3
    NULL_CHECKSUM = 15


NULL_CHECKSUM_U32 = bytes([0x00, 0x00, 0x00, 0x00])
