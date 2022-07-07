import enum
import struct


class PrintFormats(enum.IntEnum):
    HEX = 0
    DEC = 1
    BIN = 2


def get_printable_data_string(
    print_format: PrintFormats, data: bytes, length: int = -1
) -> str:
    """Returns the TM data in a clean printable hex string format
    :return: The string
    """
    if length == -1:
        length = len(data)
    data_to_print = data[:length]
    if print_format == PrintFormats.HEX:
        return f'hex [{data_to_print.hex(sep=",", bytes_per_sep=1)}]'
    elif print_format == PrintFormats.DEC:
        if len(data_to_print) == 0:
            return "dec []"
        elif len(data_to_print) == 1:
            return f"dec [{data_to_print[0]}]"
        elif len(data_to_print) >= 2:
            string_to_print = "dec ["
            for idx in range(len(data_to_print) - 1):
                string_to_print += f"{data_to_print[idx]},"
            string_to_print += f"{data_to_print[length - 1]}]"
            return string_to_print
    elif print_format == PrintFormats.BIN:
        if len(data_to_print) == 0:
            return "bin []"
        elif len(data_to_print) == 1:
            return f"bin [0:{data_to_print[0]:08b}]"
        elif len(data_to_print) >= 2:
            string_to_print = "bin [\n"
            for idx in range(len(data_to_print)):
                string_to_print += f"{idx}:{data_to_print[idx]:08b}\n"
            string_to_print += f"]"
            return string_to_print


class IntByteConversion:
    @staticmethod
    def signed_struct_specifier(byte_num: int) -> str:
        if byte_num not in [1, 2, 4, 8]:
            raise ValueError("Invalid byte number, must be one of [1, 2, 4, 8]")
        if byte_num == 1:
            return "!b"
        elif byte_num == 2:
            return "!h"
        elif byte_num == 4:
            return "!i"
        elif byte_num == 8:
            return "!q"

    @staticmethod
    def unsigned_struct_specifier(byte_num: int) -> str:
        if byte_num not in [1, 2, 4, 8]:
            raise ValueError("Invalid byte number, must be one of [1, 2, 4, 8]")
        if byte_num == 1:
            return "!B"
        elif byte_num == 2:
            return "!H"
        elif byte_num == 4:
            return "!I"
        elif byte_num == 8:
            return "!Q"

    @staticmethod
    def to_signed(byte_num: int, val: int) -> bytes:
        """Convert number of bytes in a field to the struct API signed format specifier,
        assuming network endianness. Raises value error if number is not inside [1, 2, 4, 8]"""
        if byte_num not in [1, 2, 4, 8]:
            raise ValueError("Invalid byte number, must be one of [1, 2, 4, 8]")
        if abs(val) > pow(2, (byte_num * 8) - 1) - 1:
            raise ValueError(
                f"Passed value larger than allows {pow(2, (byte_num * 8) - 1) - 1}"
            )
        return struct.pack(IntByteConversion.signed_struct_specifier(byte_num), val)

    @staticmethod
    def to_unsigned(byte_num: int, val: int) -> bytes:
        """Convert number of bytes in a field to the struct API unsigned format specifier,
        assuming network endianness. Raises value error if number is not inside [1, 2, 4, 8]"""
        if byte_num not in [1, 2, 4, 8]:
            raise ValueError("Invalid byte number, must be one of [1, 2, 4, 8]")
        if val > pow(2, byte_num * 8) - 1:
            raise ValueError(f"Passed value larger than allows {pow(2, byte_num) - 1}")
        return struct.pack(IntByteConversion.unsigned_struct_specifier(byte_num), val)
