import enum


class LenInBytes(enum.IntEnum):
    ONE_BYTE = 1
    TWO_BYTES = 2
    FOUR_BYTES = 4
    EIGHT_BYTES = 8
    GLOBAL = 90
    NONE = 99


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
