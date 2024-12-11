"""This modules contains generic CRC support."""

from crcmod.predefined import mkPredefinedCrcFun

#: CRC calculator function as specified in the PUS standard B.1
#: Generated with :py:func:`crcmod.predefined.mkPredefinedCrcFun` with the
#: `crc-ccitt-false` as the CRC name.
CRC16_CCITT_FUNC = mkPredefinedCrcFun(crc_name="crc-ccitt-false")
