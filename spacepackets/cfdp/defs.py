from __future__ import annotations
import enum
import struct

from spacepackets.util import IntByteConversion


class PduType(enum.IntEnum):
    FILE_DIRECTIVE = 0
    FILE_DATA = 1


class Direction(enum.IntEnum):
    """This is used for PDU forwarding"""

    TOWARDS_RECEIVER = 0
    TOWARDS_SENDER = 1


class TransmissionModes(enum.IntEnum):
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


class FaultHandlerCodes(enum.IntEnum):
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
class ChecksumTypes(enum.IntEnum):
    # Modular legacy checksum
    MODULAR = 0
    CRC_32_PROXIMITY_1 = 1
    CRC_32C = 2
    # Polynomial: 0x4C11DB7. This is the preferred checksum for now.
    CRC_32 = 3
    NULL_CHECKSUM = 15


class UnsignedByteField:
    def __init__(self, val: int, byte_len: int):
        self.byte_len = byte_len
        self.value = val

    @property
    def byte_len(self):
        return self._byte_len

    @byte_len.setter
    def byte_len(self, byte_len: int):
        if byte_len not in [1, 2, 4, 8]:
            # I really have no idea why anyone would use other values than these
            raise ValueError(
                "Only 1, 2, 4 and 8 bytes are allowed as an entity ID length"
            )
        self._byte_len = byte_len

    @property
    def value(self):
        return self._val

    @value.setter
    def value(self, val: int):
        if val > pow(2, self.byte_len * 8) - 1:
            raise ValueError(
                f"Passed value larger than allowed {pow(2, self.byte_len * 8) - 1}"
            )
        self._val = val

    def as_bytes(self) -> bytes:
        return IntByteConversion.to_unsigned(self.byte_len, self.value)

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(entity_id={self.value!r}, "
            f"byte_len={self.byte_len!r})"
        )

    def __int__(self):
        return self.value

    def __eq__(self, other: UnsignedByteField):
        return self.value == other.value and self.byte_len == other.byte_len

    def __hash__(self):
        return hash((self.value, self.byte_len))


class ByteFieldU8(UnsignedByteField):
    """Concrete variant of a variable length byte field which has 1 byte"""

    def __init__(self, val: int):
        super().__init__(val, 1)

    @classmethod
    def from_bytes(cls, stream: bytes) -> ByteFieldU8:
        if len(stream) < 1:
            raise ValueError(
                "Passed stream not large enough, should be at least 1 byte"
            )
        return cls(stream[0])


class ByteFieldU16(UnsignedByteField):
    """Concrete variant of a variable length byte field which has 2 bytes"""

    def __init__(self, val: int):
        super().__init__(val, 2)

    @classmethod
    def from_bytes(cls, stream: bytes) -> ByteFieldU16:
        if len(stream) < 2:
            raise ValueError(
                "Passed stream not large enough, should be at least 2 byte"
            )
        return cls(
            struct.unpack(IntByteConversion.unsigned_struct_specifier(2), stream[0:2])[
                0
            ]
        )


class ByteFieldU32(UnsignedByteField):
    """Concrete variant of a variable length byte field which has 4 bytes"""

    def __init__(self, val: int):
        super().__init__(val, 4)

    @classmethod
    def from_bytes(cls, stream: bytes) -> ByteFieldU32:
        if len(stream) < 4:
            raise ValueError(
                "Passed stream not large enough, should be at least 4 byte"
            )
        return cls(
            struct.unpack(IntByteConversion.unsigned_struct_specifier(4), stream[0:4])[
                0
            ]
        )


class ByteFieldGenerator:
    @staticmethod
    def from_bytes(byte_len: int, stream: bytes) -> UnsignedByteField:
        if byte_len == 1:
            return ByteFieldU8.from_bytes(stream)
        elif byte_len == 2:
            return ByteFieldU16.from_bytes(stream)
        elif byte_len == 4:
            return ByteFieldU32.from_bytes(stream)
