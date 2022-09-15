from __future__ import annotations


class CfdpLv:
    def __init__(self, value: bytes):
        """This class encapsulates CFDP LV fields

        :raise ValueError: If value is invalid and serilization is enabled or if length of bytearray
            is too large
        :param value:
        """
        if len(value) > 255:
            raise ValueError("Length too large for LV field")
        self.len = len(value)
        self.value = value

    @property
    def packet_len(self):
        """Returns length of full LV packet"""
        return self.len + 1

    def pack(self) -> bytearray:
        packet = bytearray()
        packet.append(self.len)
        if self.len > 0:
            packet.extend(self.value)
        return packet

    @classmethod
    def unpack(cls, raw_bytes: bytes) -> CfdpLv:
        """Parses LV field at the start of the given bytearray

        :raise ValueError: Invalid length found
        """
        detected_len = raw_bytes[0]
        if 1 + detected_len > len(raw_bytes):
            raise ValueError("Detected length exceeds size of passed bytearray")
        if detected_len == 0:
            return cls(value=bytes())
        return cls(value=raw_bytes[1 : 1 + detected_len])

    def __repr__(self):
        return f"{self.__class__.__name__}(value={self.value!r})"

    def __str__(self):
        return f"CFDP LV with data 0x[{self.value.hex(sep=',')}] of length {len(self.value)}"

    def __eq__(self, other):
        return self.value == other.value
