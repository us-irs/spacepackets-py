from typing import Optional
from spacepackets.cfdp.tlv.defs import TlvType


class InvalidCrc(Exception):
    def __int__(self, crc16: int, message: Optional[str] = None):
        self.crc16 = crc16
        self.message = message
        if self.message is None:
            self.message = f"invalid crc with value {crc16:#04x} detected"
        super().__init__(self.message)


class TlvTypeMissmatch(Exception):
    def __init__(self, found: TlvType, expected: TlvType):
        self.found = found
        self.expected = expected
        super().__init__(f"Expected TLV {self.expected}, found {self.found}")
