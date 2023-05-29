from crcmod.predefined import mkPredefinedCrcFun

#: CRC calculator function as specified in the PUS standard B.1
CRC16_CCITT_FUNC = mkPredefinedCrcFun(crc_name="crc-ccitt-false")
