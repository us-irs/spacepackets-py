from __future__ import annotations
import enum
import struct
from dataclasses import dataclass


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
        return bytearray(
            struct.pack(byte_num_to_unsigned_struct_specifier(num_bytes), self.val)
        )

    def len(self):
        """Return the length in bytes. This will raise a ValueError for non-byte-aligned
        PFC values"""
        return self.check_pfc(self.pfc)

    @classmethod
    def unpack(cls, data: bytes, pfc: int):
        num_bytes = cls.check_pfc(pfc)
        return cls(
            pfc,
            struct.unpack(
                byte_num_to_unsigned_struct_specifier(num_bytes), data[0:num_bytes]
            )[0],
        )

    @staticmethod
    def check_pfc(pfc: int) -> int:
        """Check for byte alignment of the PFC. Do not use this if to plan to pack multiple
        enumerations into one byte
        """
        num_bytes = round(pfc / 8)
        if num_bytes not in [1, 2, 4, 8]:
            raise ValueError("Invalid PFC, not byte aligned")
        return num_bytes

    def __repr__(self):
        return f"{self.__class__.__name__}(pfc={self.pfc!r}, val={self.val!r})"

    def __eq__(self, other: PacketFieldEnum):
        return self.pfc == other.pfc and self.val == other.val


def byte_num_to_signed_struct_specifier(byte_num: int) -> str:
    """Convert number of bytes in a field to the struct API signed format specifier,
    assuming network endianness. Raises value error if number is not inside [1, 2, 4, 8]"""
    if byte_num == 1:
        return "!b"
    elif byte_num == 2:
        return "!h"
    elif byte_num == 4:
        return "!i"
    elif byte_num == 8:
        return "!q"
    raise ValueError("Invalid number of bytes specified")


def byte_num_to_unsigned_struct_specifier(byte_num: int) -> str:
    """Convert number of bytes in a field to the struct API unsigned format specifier,
    assuming network endianness. Raises value error if number is not inside [1, 2, 4, 8]"""
    if byte_num == 1:
        return "!B"
    elif byte_num == 2:
        return "!H"
    elif byte_num == 4:
        return "!I"
    elif byte_num == 8:
        return "!Q"
    raise ValueError("Invalid number of bytes specified")