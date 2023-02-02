from __future__ import annotations
import enum
import struct
from dataclasses import dataclass

from spacepackets import BytesTooShortError
from spacepackets.util import IntByteConversion


class Ptc(enum.IntEnum):
    BOOLEAN = 1
    ENUMERATED = 2
    UNSIGNED = 3
    SIGNED = 4
    # Float or double values
    REAL = 5
    BIT_STRING = 6
    OCTET_STRING = 7
    CHARACTER_STRING = 8
    ABSOLUTE_TIME = 9
    RELATIVE_TIME = 10
    DEDUCED = 11
    PACKET = 12


class PfcUnsigned(enum.IntEnum):
    FOUR_BIT = 0
    FIVE_BIT = 1
    SIX_BIT = 2
    SEVEN_BIT = 3
    ONE_BYTE = 4
    NINE_BIT = 5
    TEN_BIT = 6
    ELEVEN_BIT = 7
    TWELVE_BIT = 8
    THIRTEEN_BIT = 9
    FOURTEEN_BIT = 10
    FIFTEEN_BIT = 11
    TWO_BYTES = 12
    THREE_BYTES = 13
    FOUR_BYTES = 14
    SIX_BYTES = 15
    EIGHT_BYTES = 16
    ONE_BIT = 17
    TWO_BIT = 18
    THREE_BIT = 19


class PfcSigned(enum.IntEnum):
    FOUR_BIT = 0
    FIVE_BIT = 1
    SIX_BIT = 2
    SEVEN_BIT = 3
    ONE_BYTE = 4
    NINE_BIT = 5
    TEN_BIT = 6
    ELEVEN_BIT = 7
    TWELVE_BIT = 8
    THIRTEEN_BIT = 9
    FOURTEEN_BIT = 10
    FIFTEEN_BIT = 11
    TWO_BYTES = 12
    THREE_BYTES = 13
    FOUR_BYTES = 14
    SIX_BYTES = 15
    EIGHT_BYTES = 16


class PfcReal(enum.IntEnum):
    FLOAT_SIMPLE_PRECISION_IEEE = 1
    DOUBLE_PRECISION_IEEE = 2
    FLOAT_PRECISION_MIL_STD_4_OCTETS = 3
    DOUBLE_PRECISION_MIL_STD_6_OCTETS = 4


@dataclass
class PacketFieldBase:
    ptc: int
    pfc: int


class PacketFieldEnum(PacketFieldBase):
    def __init__(self, pfc: int, val: int):
        super().__init__(ptc=Ptc.ENUMERATED, pfc=pfc)
        self.check_pfc(pfc)
        self.val = val

    @classmethod
    def with_byte_size(cls, num_bytes: int, val: int):
        return cls(num_bytes * 8, val)

    def pack(self) -> bytearray:
        num_bytes = self.check_pfc(self.pfc)
        return bytearray(IntByteConversion.to_unsigned(num_bytes, self.val))

    def len(self):
        """Return the length in bytes. This will raise a ValueError for non-byte-aligned
        PFC values."""
        return self.check_pfc(self.pfc)

    @classmethod
    def unpack(cls, data: bytes, pfc: int):
        """Construct from a raw bytestream.

        :raises BytesTooShortError: Raw bytestream too short.
        """
        num_bytes = cls.check_pfc(pfc)
        if num_bytes > len(data):
            raise BytesTooShortError(num_bytes, len(data))
        return cls(
            pfc,
            struct.unpack(
                IntByteConversion.unsigned_struct_specifier(num_bytes),
                data[0:num_bytes],
            )[0],
        )

    @staticmethod
    def check_pfc(pfc: int) -> int:
        """Check for byte alignment of the PFC. Do not use this if to plan to pack multiple
        enumerations into one byte
        """
        num_bytes = int(round(pfc / 8))
        if num_bytes not in [1, 2, 4, 8]:
            raise ValueError("Invalid PFC, not byte aligned")
        return num_bytes

    def __repr__(self):
        return f"{self.__class__.__name__}(pfc={self.pfc!r}, val={self.val!r})"

    def __eq__(self, other: PacketFieldEnum):
        return self.pfc == other.pfc and self.val == other.val


class PacketFieldU8(PacketFieldEnum):
    def __init__(self, val: int):
        super().__init__(pfc=8, val=val)


class PacketFieldU16(PacketFieldEnum):
    def __init__(self, val: int):
        super().__init__(pfc=16, val=val)


class PacketFieldU32(PacketFieldEnum):
    def __init__(self, val: int):
        super().__init__(pfc=32, val=val)
