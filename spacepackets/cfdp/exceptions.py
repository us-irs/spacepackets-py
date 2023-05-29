from typing import Optional


class InvalidCrc(Exception):
    def __int__(self, crc16: int, message: Optional[str] = None):
        self.crc16 = crc16
        self.message = message
        if self.message is None:
            self.message = f"invalid crc with value {crc16:#04x} detected"
        super().__init__(self.message)
