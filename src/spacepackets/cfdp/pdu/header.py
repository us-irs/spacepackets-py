from __future__ import annotations

import abc
import struct

import fastcrc

from spacepackets.cfdp.conf import (
    PduConfig,
)
from spacepackets.cfdp.defs import (
    CFDP_VERSION_2,
    CrcFlag,
    Direction,
    InvalidCrcError,
    LargeFileFlag,
    LenInBytes,
    PduType,
    SegmentationControl,
    SegmentMetadataFlag,
    TransmissionMode,
    UnsupportedCfdpVersionError,
)
from spacepackets.exceptions import BytesTooShortError
from spacepackets.util import ByteFieldGenerator, UnsignedByteField


class AbstractPduBase(abc.ABC):
    """Encapsulate common functions for PDU. PDU or Packet Data Units are the base data unit
    which are exchanged for CFDP procedures. Each PDU has a common header and this class provides
    abstract methods to access fields of that common header.
    For more, information, refer to CCSDS 727.0-B-5 p.75.
    The default implementation provided in this library for this abstract class is the
    :py:class:`PduHeader` class.
    """

    VERSION_BITS = 0b0010_0000
    FIXED_LENGTH = 4

    @abc.abstractmethod
    def pack(self) -> bytearray:
        pass

    @property
    @abc.abstractmethod
    def pdu_header(self) -> PduHeader:
        # Could return abstract class here but I think returning the concrete implementation
        # provided here is ok for now.
        pass

    @property
    @abc.abstractmethod
    def pdu_type(self) -> PduType:
        pass

    @property
    @abc.abstractmethod
    def direction(self) -> Direction:
        pass

    @property
    @abc.abstractmethod
    def file_flag(self) -> LargeFileFlag:
        pass

    @file_flag.setter
    @abc.abstractmethod
    def file_flag(self, file_flag: LargeFileFlag) -> None:
        pass

    @property
    @abc.abstractmethod
    def header_len(self) -> int:
        pass

    @property
    @abc.abstractmethod
    def source_entity_id(self) -> UnsignedByteField:
        pass

    @property
    @abc.abstractmethod
    def dest_entity_id(self) -> UnsignedByteField:
        pass

    @property
    @abc.abstractmethod
    def transmission_mode(self) -> TransmissionMode:
        pass

    @property
    @abc.abstractmethod
    def transaction_seq_num(self) -> UnsignedByteField:
        pass

    @property
    @abc.abstractmethod
    def pdu_data_field_len(self) -> int:
        pass

    @pdu_data_field_len.setter
    @abc.abstractmethod
    def pdu_data_field_len(self, pdu_data_field_len: int) -> int:
        pass

    @property
    @abc.abstractmethod
    def crc_flag(self) -> CrcFlag:
        pass

    @crc_flag.setter
    @abc.abstractmethod
    def crc_flag(self, crc_flag: CrcFlag) -> None:
        pass

    @property
    def packet_len(self) -> int:
        return self.pdu_data_field_len + self.header_len

    @property
    def large_file_flag_set(self) -> bool:
        return self.file_flag == LargeFileFlag.LARGE

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AbstractPduBase):
            return False
        return (
            self.pdu_type == other.pdu_type
            and self.file_flag == other.file_flag
            and self.crc_flag == other.crc_flag
            and self.dest_entity_id == other.dest_entity_id
            and self.source_entity_id == other.source_entity_id
            and self.packet_len == other.packet_len
        )

    def __hash__(self) -> int:
        return hash(
            (
                self.pdu_type,
                self.file_flag,
                self.crc_flag,
                self.dest_entity_id,
                self.source_entity_id,
                self.packet_len,
            )
        )

    @staticmethod
    def header_len_from_raw(data: bytes | bytearray) -> int:
        entity_id_len = ((data[3] >> 4) & 0b111) + 1
        seq_num_len = (data[3] & 0b111) + 1
        return AbstractPduBase.FIXED_LENGTH + 2 * entity_id_len + seq_num_len


class PduHeader(AbstractPduBase):
    """Concrete implementation of the abstract :py:class:`AbstractPduBase` class"""

    def __init__(
        self,
        pdu_type: PduType,
        segment_metadata_flag: SegmentMetadataFlag,
        pdu_data_field_len: int,
        pdu_conf: PduConfig,
    ):
        """Constructor for PDU header

        :param pdu_type:
        :param segment_metadata_flag:
        :param pdu_data_field_len:
        :param pdu_conf:
        :raise ValueError: If some field are invalid or default values were unset
        """
        self._pdu_type = pdu_type
        self.pdu_conf = pdu_conf
        self.pdu_data_field_len = pdu_data_field_len

        self.set_entity_ids(
            source_entity_id=pdu_conf.source_entity_id,
            dest_entity_id=pdu_conf.dest_entity_id,
        )
        self.transaction_seq_num = pdu_conf.transaction_seq_num
        self.segment_metadata_flag = segment_metadata_flag

    @property
    def pdu_header(self) -> PduHeader:
        return self

    @property
    def pdu_type(self) -> PduType:
        return self._pdu_type

    @pdu_type.setter
    def pdu_type(self, pdu_type: PduType) -> None:
        self._pdu_type = pdu_type

    @property
    def source_entity_id(self) -> UnsignedByteField:
        return self.pdu_conf.source_entity_id

    @property
    def dest_entity_id(self) -> UnsignedByteField:
        return self.pdu_conf.dest_entity_id

    @property
    def transmission_mode(self) -> TransmissionMode:
        return self.pdu_conf.trans_mode

    def set_entity_ids(
        self, source_entity_id: UnsignedByteField, dest_entity_id: UnsignedByteField
    ) -> None:
        """Both IDs must be set at once because they must have the same length as well
        :param source_entity_id:
        :param dest_entity_id:
        :return:
        """
        if source_entity_id.byte_len != dest_entity_id.byte_len:
            raise ValueError("Length of destination ID and source ID are not the same")
        self.pdu_conf.source_entity_id = source_entity_id
        self.pdu_conf.dest_entity_id = dest_entity_id

    @property
    def transaction_seq_num(self) -> UnsignedByteField:
        return self.pdu_conf.transaction_seq_num

    @transaction_seq_num.setter
    def transaction_seq_num(self, transaction_seq_num: UnsignedByteField) -> None:
        self.pdu_conf.transaction_seq_num = transaction_seq_num

    @property
    def file_flag(self) -> LargeFileFlag:
        return self.pdu_conf.file_flag

    @file_flag.setter
    def file_flag(self, file_flag: LargeFileFlag) -> None:
        self.pdu_conf.file_flag = file_flag

    @property
    def crc_flag(self) -> CrcFlag:
        return self.pdu_conf.crc_flag

    @crc_flag.setter
    def crc_flag(self, crc_flag: CrcFlag) -> None:
        self.pdu_conf.crc_flag = crc_flag

    @transmission_mode.setter
    def transmission_mode(self, trans_mode: TransmissionMode) -> None:
        self.pdu_conf.trans_mode = trans_mode

    @property
    def direction(self) -> Direction:
        return self.pdu_conf.direction

    @direction.setter
    def direction(self, direction: Direction) -> None:
        self.pdu_conf.direction = direction

    @property
    def seg_ctrl(self) -> SegmentationControl:
        return self.pdu_conf.seg_ctrl

    @seg_ctrl.setter
    def seg_ctrl(self, seg_ctrl: SegmentationControl) -> None:
        self.pdu_conf.seg_ctrl = seg_ctrl

    @property
    def pdu_data_field_len(self) -> int:
        return self._pdu_data_field_len

    @pdu_data_field_len.setter
    def pdu_data_field_len(self, new_len: int) -> None:
        """Set the PDU data field length.

        :param new_len:
        :raises ValueError: Value too large
        :return:
        """
        if new_len > pow(2, 16) - 1:
            raise ValueError
        self._pdu_data_field_len = new_len

    @property
    def header_len(self) -> int:
        """Get length of PDU header when packing it"""
        return (
            self.FIXED_LENGTH
            + 2 * self.source_entity_id.byte_len
            + self.transaction_seq_num.byte_len
        )

    def pack(self) -> bytearray:
        header = bytearray()
        header.append(
            CFDP_VERSION_2 << 5
            | (self.pdu_type << 4)
            | (self.pdu_conf.direction << 3)
            | (self.pdu_conf.trans_mode << 2)
            | (self.pdu_conf.crc_flag << 1)
            | self.pdu_conf.file_flag
        )
        header.append((self.pdu_data_field_len >> 8) & 0xFF)
        header.append(self.pdu_data_field_len & 0xFF)
        header.append(
            self.pdu_conf.seg_ctrl << 7
            | ((self.source_entity_id.byte_len - 1) << 4)
            | self.segment_metadata_flag << 3
            | (self.transaction_seq_num.byte_len - 1)
        )
        header.extend(self.pdu_conf.source_entity_id.as_bytes)
        header.extend(self.pdu_conf.transaction_seq_num.as_bytes)
        header.extend(self.pdu_conf.dest_entity_id.as_bytes)
        return header

    @classmethod
    def __empty(cls) -> PduHeader:
        empty_conf = PduConfig.empty()
        return cls(
            pdu_type=PduType.FILE_DIRECTIVE,
            segment_metadata_flag=SegmentMetadataFlag.NOT_PRESENT,
            pdu_data_field_len=0,
            pdu_conf=empty_conf,
        )

    @classmethod
    def unpack(cls, data: bytes | bytearray) -> PduHeader:
        """Unpack a raw bytearray into the PDU header object representation.

        :param data:
        :raises BytesTooShortError: Passed bytearray is too short.
        :raises UnsupportedCfdpVersion: CFDP version not supported. Only version 2 related to
            CFDP version CCSDS 727.0-B-5 is supported.
        :return: Unpacked object representation of a PDU header
        """
        if len(data) < cls.FIXED_LENGTH:
            raise BytesTooShortError(cls.FIXED_LENGTH, len(data))
        pdu_header = cls.__empty()
        version_raw = (data[0] >> 5) & 0b111
        if version_raw != CFDP_VERSION_2:
            raise UnsupportedCfdpVersionError(version_raw)
        pdu_header._pdu_type = PduType((data[0] & 0x10) >> 4)
        pdu_header.direction = Direction((data[0] & 0x08) >> 3)
        pdu_header.transmission_mode = TransmissionMode((data[0] & 0x04) >> 2)
        pdu_header.crc_flag = CrcFlag((data[0] & 0x02) >> 1)
        pdu_header.file_flag = LargeFileFlag(data[0] & 0x01)
        pdu_header.pdu_data_field_len = data[1] << 8 | data[2]
        pdu_header.seg_ctrl = SegmentationControl((data[3] & 0x80) >> 7)
        expected_len_entity_ids = cls.check_len_in_bytes(((data[3] >> 4) & 0b111) + 1)
        pdu_header.segment_metadata_flag = SegmentMetadataFlag((data[3] >> 3) & 0b1)
        expected_len_seq_num = cls.check_len_in_bytes((data[3] & 0b111) + 1)
        expected_remaining_len = 2 * expected_len_entity_ids + expected_len_seq_num
        if expected_remaining_len + cls.FIXED_LENGTH > len(data):
            raise BytesTooShortError(expected_remaining_len + cls.FIXED_LENGTH, len(data))
        current_idx = 4
        source_entity_id = ByteFieldGenerator.from_bytes(
            expected_len_entity_ids,
            data[current_idx : current_idx + expected_len_entity_ids],
        )
        current_idx += expected_len_entity_ids
        pdu_header.transaction_seq_num = ByteFieldGenerator.from_bytes(
            expected_len_seq_num,
            data[current_idx : current_idx + expected_len_seq_num],
        )
        current_idx += expected_len_seq_num
        dest_entity_id = ByteFieldGenerator.from_bytes(
            expected_len_entity_ids,
            data[current_idx : current_idx + expected_len_entity_ids],
        )
        pdu_header.set_entity_ids(source_entity_id=source_entity_id, dest_entity_id=dest_entity_id)
        return pdu_header

    def verify_length_and_checksum(self, data: bytes | bytearray) -> int:
        if len(data) < self.packet_len:
            raise BytesTooShortError(self.packet_len, len(data))
        if (
            self.pdu_conf.crc_flag == CrcFlag.WITH_CRC
            and fastcrc.crc16.ibm_3740(bytes(data[: self.packet_len])) != 0
        ):
            raise InvalidCrcError(
                struct.unpack("!H", data[self.packet_len - 2 : self.packet_len])[0]
            )
        return self.packet_len

    @staticmethod
    def check_len_in_bytes(detected_len: int) -> LenInBytes:
        if detected_len not in [1, 2, 4, 8]:
            raise ValueError("Unsupported length field detected. Must be in [1, 2, 4, 8]")
        return LenInBytes(detected_len)

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(pdu_type={self.pdu_type!r},"
            f"segment_metadata_flag={self.segment_metadata_flag!r},"
            f"pdu_data_field_len={self.pdu_data_field_len!r},"
            f"pdu_conf={self.pdu_conf!r})"
        )
