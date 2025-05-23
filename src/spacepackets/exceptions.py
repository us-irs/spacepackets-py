import deprecation


class BytesTooShortError(ValueError):
    """When unpacking something from raw :py:class:`bytes`, the length of the bytearray was too
    short."""

    def __init__(self, expected_len: int, bytes_len: int):
        super().__init__(f"bytearray with length {bytes_len} shorter than expected {expected_len}")
        self.expected_len = expected_len
        self.bytes_len = bytes_len


class InvalidCrcCcitt16Error(Exception):
    def __init__(self, data: bytes):
        self.data = data


@deprecation.deprecated(
    deprecated_in="0.29.0",
    details="Use InvalidCrcCcitt16Error instead.",
)
class InvalidCrcCcitt16(InvalidCrcCcitt16Error):  # noqa: N818
    pass
