from __future__ import annotations
import enum
from spacepackets.log import get_console_logger


class TlvTypes(enum.IntEnum):
    FILESTORE_REQUEST = 0x00
    FILESTORE_RESPONSE = 0x01
    MESSAGE_TO_USER = 0x02
    FAULT_HANDLER = 0x04
    FLOW_LABEL = 0x05
    ENTITY_ID = 0x06


class CfdpTlv:
    """Encapsulates the CFDP TLV (type-length-value) format.
    For more information, refer to CCSDS 727.0-B-5 p.77
    """
    MINIMAL_LEN = 2

    def __init__(
            self,
            tlv_type: TlvTypes,
            value: bytes
    ):
        """Constructor for TLV field.

        :param tlv_type:
        :param value:
        :raise ValueError: Length invalid or value length not equal to specified length
        """
        self.length = len(value)
        if self.length > 255:
            logger = get_console_logger()
            logger.warning('Length larger than allowed 255 bytes')
            raise ValueError
        self.tlv_type = tlv_type
        self.value = value

    def pack(self) -> bytearray:
        tlv_data = bytearray()
        tlv_data.append(self.tlv_type)
        tlv_data.append(self.length)
        tlv_data.extend(self.value)
        return tlv_data

    @classmethod
    def unpack(cls, raw_bytes: bytes) -> CfdpTlv:
        """Parses LV field at the start of the given bytearray

        :param raw_bytes:
        :raise ValueError: Invalid format of the raw bytearray or type field invalid
        :return:
        """
        if len(raw_bytes) < 2:
            logger = get_console_logger()
            logger.warning('Invalid length for TLV field, less than 2')
            raise ValueError
        try:
            tlv_type = TlvTypes(raw_bytes[0])
        except ValueError:
            logger = get_console_logger()
            logger.warning(
                f'TLV field invalid, found value {raw_bytes[0]} is not a possible TLV parameter'
            )
            raise ValueError

        value = bytearray()
        if len(raw_bytes) > 2:
            length = raw_bytes[1]
            if 2 + length > len(raw_bytes):
                logger = get_console_logger()
                logger.warning(f'Detected TLV length exceeds size of passed bytearray')
                raise ValueError
            value.extend(raw_bytes[2: 2 + length])
        return cls(
            tlv_type=tlv_type,
            value=value
        )

    def get_total_length(self) -> int:
        return self.MINIMAL_LEN + len(self.value)
