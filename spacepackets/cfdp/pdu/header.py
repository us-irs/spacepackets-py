from __future__ import annotations

import abc

from spacepackets.cfdp.defs import (
    LargeFileFlag,
    PduType,
    SegmentMetadataFlag,
    CrcFlag,
    TransmissionMode,
    Direction,
    SegmentationControl,
    LenInBytes,
    CFDP_VERSION_2,
    UnsupportedCfdpVersion,
)
from spacepackets.cfdp.conf import (
    PduConfig,
)
from spacepackets.exceptions import BytesTooShortError
from spacepackets.util import UnsignedByteField, ByteFieldGenerator


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
    def pdu_type(self) -> PduType:
        pass

    @property
    @abc.abstractmethod
    def file_flag(self) -> LargeFileFlag:
        pass

    @file_flag.setter
    @abc.abstractmethod
    def file_flag(self, file_flag: LargeFileFlag):
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
    def crc_flag(self):
        pass

    @crc_flag.setter
    @abc.abstractmethod
    def crc_flag(self, crc_flag: CrcFlag):
        pass

    @property
    def packet_len(self) -> int:
        return self.pdu_data_field_len + self.header_len

    @property
    def large_file_flag_set(self) -> bool:
        return self.file_flag == LargeFileFlag.LARGE

    def __eq__(self, other: AbstractPduBase):
        return (
            self.pdu_type == other.pdu_type
            and self.file_flag == other.file_flag
            and self.crc_flag == other.crc_flag
            and self.dest_entity_id == other.dest_entity_id
            and self.source_entity_id == other.source_entity_id
            and self.packet_len == other.packet_len
        )

    @staticmethod
    def header_len_from_raw(data: bytes):
        entity_id_len = (data[3] >> 4) & 0b111
        seq_num_len = data[3] & 0b111
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
    def pdu_type(self) -> PduType:
        return self._pdu_type

    @pdu_type.setter
    def pdu_type(self, pdu_type: PduType):
        self._pdu_type = pdu_type

    @property
    def source_entity_id(self):
        return self.pdu_conf.source_entity_id

    @property
    def dest_entity_id(self):
        return self.pdu_conf.dest_entity_id

    def set_entity_ids(
        self, source_entity_id: UnsignedByteField, dest_entity_id: UnsignedByteField
    ):
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
    def transaction_seq_num(self):
        return self.pdu_conf.transaction_seq_num

    @transaction_seq_num.setter
    def transaction_seq_num(self, transaction_seq_num: UnsignedByteField):
        self.pdu_conf.transaction_seq_num = transaction_seq_num

    @property
    def file_flag(self):
        return self.pdu_conf.file_flag

    @file_flag.setter
    def file_flag(self, file_flag: LargeFileFlag):
        self.pdu_conf.file_flag = file_flag

    @property
    def crc_flag(self):
        return self.pdu_conf.crc_flag

    @crc_flag.setter
    def crc_flag(self, crc_flag: CrcFlag):
        self.pdu_conf.crc_flag = crc_flag

    @property
    def trans_mode(self):
        return self.pdu_conf.trans_mode

    @trans_mode.setter
    def trans_mode(self, trans_mode: TransmissionMode):
        self.pdu_conf.trans_mode = trans_mode

    @property
    def direction(self):
        return self.pdu_conf.direction

    @direction.setter
    def direction(self, direction: Direction):
        self.pdu_conf.direction = direction

    @property
    def seg_ctrl(self):
        return self.pdu_conf.seg_ctrl

    @seg_ctrl.setter
    def seg_ctrl(self, seg_ctrl: SegmentationControl):
        self.pdu_conf.seg_ctrl = seg_ctrl

    @property
    def pdu_data_field_len(self):
        return self._pdu_data_field_len

    @pdu_data_field_len.setter
    def pdu_data_field_len(self, new_len: int):
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
            | self.source_entity_id.byte_len << 4
            | self.segment_metadata_flag << 3
            | self.transaction_seq_num.byte_len
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
    def unpack(cls, data: bytes) -> PduHeader:
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
            raise UnsupportedCfdpVersion(version_raw)
        pdu_header._pdu_type = (data[0] & 0x10) >> 4
        pdu_header.direction = (data[0] & 0x08) >> 3
        pdu_header.trans_mode = (data[0] & 0x04) >> 2
        pdu_header.crc_flag = (data[0] & 0x02) >> 1
        pdu_header.file_flag = LargeFileFlag(data[0] & 0x01)
        pdu_header.pdu_data_field_len = data[1] << 8 | data[2]
        pdu_header.segmentation_control = SegmentationControl((data[3] & 0x80) >> 7)
        expected_len_entity_ids = cls.check_len_in_bytes((data[3] & 0x70) >> 4)
        pdu_header.segment_metadata_flag = SegmentMetadataFlag((data[3] & 0x08) >> 3)
        expected_len_seq_num = cls.check_len_in_bytes(data[3] & 0x07)
        expected_remaining_len = 2 * expected_len_entity_ids + expected_len_seq_num
        if expected_remaining_len + cls.FIXED_LENGTH > len(data):
            raise BytesTooShortError(
                expected_remaining_len + cls.FIXED_LENGTH, len(data)
            )
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
        pdu_header.set_entity_ids(
            source_entity_id=source_entity_id, dest_entity_id=dest_entity_id
        )
        return pdu_header

    @staticmethod
    def check_len_in_bytes(detected_len: int) -> LenInBytes:
        if detected_len not in [1, 2, 4, 8]:
            raise ValueError(
                "Unsupported length field detected. Must be in [1, 2, 4, 8]"
            )
        return LenInBytes(detected_len)

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(pdu_type={self.pdu_type!r},"
            f"segment_metadata_flag={self.segment_metadata_flag!r},"
            f"pdu_data_field_len={self.pdu_data_field_len!r},"
            f"pdu_conf={self.pdu_conf!r})"
        )
