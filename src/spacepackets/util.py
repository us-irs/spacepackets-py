from __future__ import annotations

import enum
import struct


class PrintFormats(enum.IntEnum):
    HEX = 0
    DEC = 1
    BIN = 2


def get_dec_data_string(data: bytes) -> str:
    if len(data) == 0:
        return "dec []"
    if len(data) == 1:
        return f"dec [{data[0]}]"
    string_to_print = "dec ["
    for idx in range(len(data) - 1):
        string_to_print += f"{data[idx]},"
    string_to_print += f"{data[len(data) - 1]}]"
    return string_to_print


def get_bin_data_string(data: bytes) -> str:
    if len(data) == 0:
        return "bin []"
    if len(data) == 1:
        return f"bin [0:{data[0]:08b}]"
    string_to_print = "bin [\n"
    for idx in range(len(data)):
        string_to_print += f"{idx}:{data[idx]:08b}\n"
    string_to_print += "]"
    return string_to_print


def get_printable_data_string(print_format: PrintFormats, data: bytes | bytearray) -> str:
    """Returns the TM data in a clean printable hex string format
    :return: The string
    """
    length = len(data)
    data_to_print = data[:length]
    if print_format == PrintFormats.HEX:
        return f"hex [{data_to_print.hex(sep=',', bytes_per_sep=1)}]"
    if print_format == PrintFormats.DEC:
        return get_dec_data_string(data)
    if print_format == PrintFormats.BIN:
        return get_bin_data_string(data)
    return None


class IntByteConversion:
    @staticmethod
    def signed_struct_specifier(byte_num: int) -> str:
        if byte_num == 1:
            return "!b"
        if byte_num == 2:
            return "!h"
        if byte_num == 4:
            return "!i"
        if byte_num == 8:
            return "!q"
        raise ValueError("Invalid byte number, must be one of [1, 2, 4, 8]")

    @staticmethod
    def unsigned_struct_specifier(byte_num: int) -> str:
        if byte_num == 1:
            return "!B"
        if byte_num == 2:
            return "!H"
        if byte_num == 4:
            return "!I"
        if byte_num == 8:
            return "!Q"
        raise ValueError(f"invalid byte number {byte_num}, must be one of [1, 2, 4, 8]")

    @staticmethod
    def to_signed(byte_num: int, val: int) -> bytes:
        """Convert number of bytes in a field to the struct API signed format specifier,
        assuming network endianness. Raises value error if number is not inside [1, 2, 4, 8]
        """
        if byte_num not in [0, 1, 2, 4, 8]:
            raise ValueError("Invalid byte number, must be one of [0, 1, 2, 4, 8]")
        if byte_num == 0:
            return b""
        if abs(val) > pow(2, (byte_num * 8) - 1) - 1:
            raise ValueError(f"Passed value larger than allows {pow(2, (byte_num * 8) - 1) - 1}")
        return struct.pack(IntByteConversion.signed_struct_specifier(byte_num), val)

    @staticmethod
    def to_unsigned(byte_num: int, val: int) -> bytes:
        """Convert number of bytes in a field to the struct API unsigned format specifier,
        assuming network endianness. Raises value error if number is not inside [1, 2, 4, 8]
        """
        if byte_num not in [0, 1, 2, 4, 8]:
            raise ValueError("Invalid byte number, must be one of [1, 2, 4, 8]")
        if byte_num == 0:
            return b""
        if val > pow(2, byte_num * 8) - 1:
            raise ValueError(f"Passed value larger than allowed {pow(2, byte_num * 8) - 1}")
        return struct.pack(IntByteConversion.unsigned_struct_specifier(byte_num), val)


class UnsignedByteField:
    """Generic base class for byte fields containing unsigned values. These are a common
    component for packet protocols or packed identifier fields. Each unsigned byte field
    has an unsigned value and a corresponding byte length. This base class implements
    commonly required boilerplate code to easily work with fields like that and convert
    them to the byte and integer representation accordingly.

    >>> field = UnsignedByteField(2, 1)
    >>> int(field)
    2
    >>> field.as_bytes.hex(sep=',')
    '02'
    >>> field = UnsignedByteField(42, 2)
    >>> int(field)
    42
    >>> field.as_bytes.hex(sep=',')
    '00,2a'
    """

    def __init__(self, val: int, byte_len: int):
        self.byte_len = byte_len
        self.value = val
        self._val_as_bytes = IntByteConversion.to_unsigned(self.byte_len, self.value)

    @classmethod
    def from_bytes(cls, raw: bytes | bytearray) -> UnsignedByteField:
        return cls(
            struct.unpack(IntByteConversion.unsigned_struct_specifier(len(raw)), raw)[0],
            len(raw),
        )

    @property
    def byte_len(self) -> int:
        return self._byte_len

    @byte_len.setter
    def byte_len(self, byte_len: int) -> None:
        UnsignedByteField.verify_byte_len(byte_len)
        self._byte_len = byte_len

    @property
    def value(self) -> int:
        return self._val

    @value.setter
    def value(self, val: int | bytes | bytearray) -> None:
        if isinstance(val, int):
            self._verify_int_value(val)
            self._val = val
            self._val_as_bytes = IntByteConversion.to_unsigned(self.byte_len, self.value)
        elif isinstance(val, (bytes, bytearray)):
            self._val, self._val_as_bytes = self._verify_bytes_value(bytes(val))

    @property
    def as_bytes(self) -> bytes:
        return self._val_as_bytes

    @staticmethod
    def verify_byte_len(byte_len: int) -> None:
        if byte_len not in [0, 1, 2, 4, 8]:
            # I really have no idea why anyone would use other values than these
            raise ValueError("Only 0, 1, 2, 4 and 8 bytes are allowed as an entity ID length")

    def _verify_int_value(self, val: int) -> None:
        if val > pow(2, self.byte_len * 8) - 1 or val < 0:
            raise ValueError(
                f"Passed value {val} larger than allowed"
                f" {pow(2, self.byte_len * 8) - 1} or negative"
            )

    def _verify_bytes_value(self, val: bytes) -> tuple[int, bytes]:
        if len(val) < self.byte_len:
            raise ValueError(f"Passed byte object {val} smaller than byte length {self.byte_len}")
        int_val = struct.unpack(
            IntByteConversion.unsigned_struct_specifier(self.byte_len),
            val[0 : self.byte_len],
        )[0]
        self._verify_int_value(int_val)
        return int_val, val[0 : self.byte_len]

    @property
    def hex_str(self) -> str | None:
        if self.byte_len == 1:
            return f"{self.value:#04x}"
        if self.byte_len == 2:
            return f"{self.value:#06x}"
        if self.byte_len == 4:
            return f"{self.value:#010x}"
        if self.byte_len == 8:
            return f"{self.value:#018x}"
        return None

    def __repr__(self):
        return f"{self.__class__.__name__}(val={self.value!r}, byte_len={self.byte_len!r})"

    def __str__(self):
        return f"dec={self.value}, hex={self.hex_str}"

    def __int__(self):
        return self.value

    def __len__(self):
        return self._byte_len

    def __eq__(self, other: object) -> bool:
        if isinstance(other, UnsignedByteField):
            return self.value == other.value and self.byte_len == other.byte_len
        if isinstance(other, bytes):
            return self._val_as_bytes == other
        raise TypeError(f"Cannot compare {self.__class__.__name__} to {other}")

    def __hash__(self):
        """Makes all unsigned byte fields usable as dictionary keys"""
        return hash((self.value, self.byte_len))

    def default_string(self, prefix: str) -> str:
        return f"{prefix}({self.value}, 0x[{self.as_bytes.hex(sep=',')}])"


class ByteFieldEmpty(UnsignedByteField):
    def __init__(self, val: int = 0):
        super().__init__(0, val)


class ByteFieldU8(UnsignedByteField):
    """Concrete variant of a variable length byte field which has a length of 1 byte"""

    def __init__(self, val: int):
        super().__init__(val, 1)

    @classmethod
    def from_u8_bytes(cls, stream: bytes | bytearray) -> ByteFieldU8:
        if len(stream) < 1:
            raise ValueError("Passed stream not large enough, should be at least 1 byte")
        return cls(stream[0])

    def __str__(self):
        return self.default_string("U8")


class ByteFieldU16(UnsignedByteField):
    """Concrete variant of a variable length byte field which has a length of 2 bytes"""

    def __init__(self, val: int):
        super().__init__(val, 2)

    @classmethod
    def from_u16_bytes(cls, stream: bytes | bytearray) -> ByteFieldU16:
        if len(stream) < 2:
            raise ValueError("Passed stream not large enough, should be at least 2 byte")
        return cls(struct.unpack(IntByteConversion.unsigned_struct_specifier(2), stream[0:2])[0])

    def __str__(self):
        return self.default_string("U16")


class ByteFieldU32(UnsignedByteField):
    """Concrete variant of a variable length byte field which has a length of 4 bytes"""

    def __init__(self, val: int):
        super().__init__(val, 4)

    @classmethod
    def from_u32_bytes(cls, stream: bytes | bytearray) -> ByteFieldU32:
        if len(stream) < 4:
            raise ValueError("passed stream not large enough, should be at least 4 bytes")
        return cls(struct.unpack(IntByteConversion.unsigned_struct_specifier(4), stream[0:4])[0])

    def __str__(self):
        return self.default_string("U32")


class ByteFieldU64(UnsignedByteField):
    """Concrete variant of a variable length byte field which has a length of 8 bytes"""

    def __init__(self, val: int):
        super().__init__(val, 8)

    @classmethod
    def from_u64_bytes(cls, stream: bytes | bytearray) -> ByteFieldU64:
        if len(stream) < 8:
            raise ValueError("passed stream not large enough, should be at least 8 byte")
        return cls(struct.unpack(IntByteConversion.unsigned_struct_specifier(8), stream[0:8])[0])

    def __str__(self):
        return self.default_string("U64")


class ByteFieldGenerator:
    """Static helpers to create the U8, U16 and U32 byte field variants of unsigned byte fields"""

    @staticmethod
    def from_int(byte_len: int, val: int) -> UnsignedByteField:
        """Generate an :py:class:`UnsignedByteField` from the byte length and a value.

        :raise ValueError: Byte length is not one of [1, 2, 4, 8]."""
        if byte_len == 1:
            return ByteFieldU8(val)
        if byte_len == 2:
            return ByteFieldU16(val)
        if byte_len == 4:
            return ByteFieldU32(val)
        if byte_len == 8:
            return ByteFieldU64(val)
        raise ValueError(f"invalid byte length {byte_len}")

    @staticmethod
    def from_bytes(byte_len: int, stream: bytes | bytearray) -> UnsignedByteField:
        """Generate an :py:class:`UnsignedByteField` from a raw bytestream and a length.

        :raise ValueError: Byte length is not one of [1, 2, 4, 8]."""
        if byte_len == 1:
            return ByteFieldU8.from_u8_bytes(stream)
        if byte_len == 2:
            return ByteFieldU16.from_u16_bytes(stream)
        if byte_len == 4:
            return ByteFieldU32.from_u32_bytes(stream)
        if byte_len == 8:
            return ByteFieldU64.from_u64_bytes(stream)
        raise ValueError(f"invalid byte length {byte_len}")


if __name__ == "__main__":
    import doctest

    doctest.testmod()
