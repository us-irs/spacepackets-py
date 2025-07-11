#!/usr/bin/env python3
import random
import timeit

from crc import Calculator, Crc16
from crcmod.predefined import mkPredefinedCrcFun
from fastcrc import crc16

#: CRC calculator function as specified in the PUS standard B.1
#: Generated with :py:func:`crcmod.predefined.mkPredefinedCrcFun` with the
#: `crc-ccitt-false` as the CRC name.
CRC16_CCITT_FUNC = mkPredefinedCrcFun(crc_name="crc-ccitt-false")
CALCULATOR = Calculator(Crc16.IBM_3740, optimized=True)


def crc_crc_lib(date: bytes) -> int:
    CALCULATOR.checksum(data_blob)


def crc_crcmod_lib(data: bytes) -> int:
    return CRC16_CCITT_FUNC(data)


def crc_fastcrc_lib(data: bytes) -> int:
    return crc16.ibm_3740(data)


data_blob = random.randbytes(1024)
crc_crclib_time = timeit.timeit(lambda: crc_crc_lib(data_blob), number=1000)
crc_crcmod_time = timeit.timeit(lambda: crc_crcmod_lib(data_blob), number=1000)
crc_fastcrc_time = timeit.timeit(lambda: crc_fastcrc_lib(data_blob), number=1000)

print(f"crc lib: {crc_crclib_time:.6f} seconds")
print(f"crcmod lib: {crc_crcmod_time:.6f} seconds")
print(f"fastcrc lib: {crc_fastcrc_time:.6f} seconds")
