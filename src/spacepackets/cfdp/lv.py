from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class CfdpLv:
    def __init__(self, value: bytes | bytearray):
        """This class encapsulates CFDP Length-Value (LV) fields.

        Raises
        -------

        ValueError
            If value is invalid and serilization is enabled or if length of bytearray is too large.
        """
        if len(value) > 255:
            raise ValueError("Length too large for LV field")
        self.value_len = len(value)
        self.value = value

    @classmethod
    def from_str(cls, string: str) -> CfdpLv:
        return cls(string.encode())

    @classmethod
    def from_path(cls, path: Path) -> CfdpLv:
        return cls.from_str(str(path))

    @property
    def packet_len(self) -> int:
        """Returns length of full LV packet"""
        return self.value_len + 1

    def pack(self) -> bytearray:
        packet = bytearray()
        packet.append(self.value_len)
        if self.value_len > 0:
            packet.extend(self.value)
        return packet

    @classmethod
    def unpack(cls, raw_bytes: bytes | bytearray) -> CfdpLv:
        """Parses LV field at the start of the given bytearray

        :raise ValueError: Invalid length found
        """
        detected_len = raw_bytes[0]
        if 1 + detected_len > len(raw_bytes):
            raise ValueError("Detected length exceeds size of passed bytearray")
        if detected_len == 0:
            return cls(value=b"")
        return cls(value=raw_bytes[1 : 1 + detected_len])

    def __repr__(self):
        return f"{self.__class__.__name__}(value={self.value!r})"

    def __str__(self):
        return f"CFDP LV with data 0x[{self.value.hex(sep=',')}] of length {len(self.value)}"

    def __eq__(self, other: object):
        if not isinstance(other, CfdpLv):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)
