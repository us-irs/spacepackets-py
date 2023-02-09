from unittest.mock import MagicMock, PropertyMock

from spacepackets.ccsds import CdsShortTimestamp, CcsdsTimeCodeId

TEST_STAMP = bytes([CcsdsTimeCodeId.CDS << 4, 1, 2, 3, 4, 5, 6])


def generic_time_provider_mock(raw_retval: bytes):
    time_stamp_provider = MagicMock(spec=CdsShortTimestamp)
    len_mock = PropertyMock(return_value=7)
    type(time_stamp_provider).len_packed = len_mock
    if len(raw_retval) != 7:
        raise ValueError("invalid raw returnvalue")
    time_stamp_provider.pack.return_value = raw_retval
    return time_stamp_provider
