import enum


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
            return 'dec []'
        elif len(data_to_print) == 1:
            return f'dec [{data_to_print[0]}]'
        elif len(data_to_print) >= 2:
            string_to_print = 'dec ['
            for idx in range(len(data_to_print) - 1):
                string_to_print += f'{data_to_print[idx]},'
            string_to_print += f'{data_to_print[length - 1]}]'
            return string_to_print
    elif print_format == PrintFormats.BIN:
        if len(data_to_print) == 0:
            return 'bin []'
        elif len(data_to_print) == 1:
            return f'bin [0:{data_to_print[0]:08b}]'
        elif len(data_to_print) >= 2:
            string_to_print = 'bin [\n'
            for idx in range(len(data_to_print)):
                string_to_print += f'{idx}:{data_to_print[idx]:08b}\n'
            string_to_print += f']'
            return string_to_print
