from __future__ import annotations

from spacepackets.log import get_console_logger
from spacepackets.cfdp.definitions import LenInBytes, FileSize, PduType, \
    SegmentMetadataFlag, CrcFlag, TransmissionModes, Direction, SegmentationControl
from spacepackets.cfdp.conf import PduConfig, get_default_pdu_crc_mode, get_default_file_size, \
    get_entity_ids


class PduHeader:
    """This class encapsulates the fixed-format PDU header.
    For more, information, refer to CCSDS 727.0-B-5 p.75"""
    VERSION_BITS = 0b0010_0000
    FIXED_LENGTH = 4

    def __init__(
            self,
            pdu_type: PduType,
            segment_metadata_flag: SegmentMetadataFlag,
            pdu_data_field_len: int,
            pdu_conf: PduConfig
    ):
        """Constructor for PDU header

        :param pdu_type:
        :param segment_metadata_flag:
        :param pdu_data_field_len:
        :param pdu_conf:
        :raise ValueError: If some field are invalid or default values were unset
        """
        self.pdu_type = pdu_type
        self.pdu_conf = pdu_conf
        self.pdu_data_field_len = pdu_data_field_len

        self.len_entity_id = 0
        self.set_entity_ids(
            source_entity_id=pdu_conf.source_entity_id, dest_entity_id=pdu_conf.dest_entity_id
        )

        self.len_transaction_seq_num = 0
        self.transaction_seq_num = pdu_conf.transaction_seq_num
        self.segment_metadata_flag = segment_metadata_flag

    @property
    def source_entity_id(self):
        return self.pdu_conf.source_entity_id

    @property
    def dest_entity_id(self):
        return self.pdu_conf.dest_entity_id

    def set_entity_ids(self, source_entity_id: bytes, dest_entity_id: bytes):
        """Both IDs must be set at once because they must have the same length as well
        :param source_entity_id:
        :param dest_entity_id:
        :return:
        """
        if source_entity_id == bytes() or dest_entity_id == bytes():
            source_entity_id, dest_entity_id = get_entity_ids()
            if source_entity_id == bytes() or dest_entity_id == bytes():
                logger = get_console_logger()
                logger.warning(
                    'Can not set default value for source entity ID or destination entity ID '
                    'because it has not been set yet'
                )
                raise ValueError
        self.pdu_conf.source_entity_id = source_entity_id
        self.pdu_conf.dest_entity_id = dest_entity_id
        try:
            self.len_entity_id = self.check_len_in_bytes(len(source_entity_id))
            dest_id_check = self.check_len_in_bytes(len(dest_entity_id))
        except ValueError:
            logger = get_console_logger()
            logger.warning('Invalid length of entity IDs passed')
            raise ValueError
        if dest_id_check != self.len_entity_id:
            logger = get_console_logger()
            logger.warning('Length of destination ID and source ID are not the same')
            raise ValueError

    @property
    def transaction_seq_num(self):
        return self.pdu_conf.transaction_seq_num

    @transaction_seq_num.setter
    def transaction_seq_num(self, transaction_seq_num: bytes):
        if transaction_seq_num is not None:
            try:
                self.len_transaction_seq_num = self.check_len_in_bytes(len(transaction_seq_num))
            except ValueError:
                logger = get_console_logger()
                logger.warning('Invalid length of transaction sequence number passed')
                raise ValueError
        self.pdu_conf.transaction_seq_num = transaction_seq_num

    @property
    def file_size(self):
        return self.pdu_conf.file_size

    @file_size.setter
    def file_size(self, file_size: FileSize):
        self.pdu_conf.file_size = file_size

    @property
    def crc_flag(self):
        return self.pdu_conf.crc_flag

    @crc_flag.setter
    def crc_flag(self, crc_flag: CrcFlag):
        if crc_flag == CrcFlag.GLOBAL_CONFIG:
            self.pdu_conf.crc_flag = get_default_pdu_crc_mode()
        else:
            self.pdu_conf.crc_flag = crc_flag

    @property
    def trans_mode(self):
        return self.pdu_conf.trans_mode

    @trans_mode.setter
    def trans_mode(self, trans_mode: TransmissionModes):
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
        """Set the PDU data field length
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
        return self.FIXED_LENGTH + 2 * self.len_entity_id + self.len_transaction_seq_num

    @property
    def pdu_len(self) -> int:
        """Get the length of the full PDU. This assumes that the length of the PDU data field
        length was already set"""
        return self.pdu_data_field_len + self.header_len

    def is_large_file(self) -> bool:
        if self.pdu_conf.file_size == FileSize.LARGE:
            return True
        else:
            return False

    def pack(self) -> bytearray:
        header = bytearray()
        header.append(
            self.VERSION_BITS | (self.pdu_type << 4) | (self.pdu_conf.direction << 3) |
            (self.pdu_conf.trans_mode << 2) | (self.pdu_conf.crc_flag << 1) |
            self.pdu_conf.file_size
        )
        header.append((self.pdu_data_field_len >> 8) & 0xff)
        header.append(self.pdu_data_field_len & 0xff)
        header.append(
            self.pdu_conf.seg_ctrl << 7 | self.len_entity_id << 4 |
            self.segment_metadata_flag << 3 | self.len_transaction_seq_num
        )
        header.extend(self.pdu_conf.source_entity_id)
        header.extend(self.pdu_conf.transaction_seq_num)
        header.extend(self.pdu_conf.dest_entity_id)
        return header

    @classmethod
    def __empty(cls) -> PduHeader:
        empty_conf = PduConfig.empty()
        return cls(
            pdu_type=PduType.FILE_DIRECTIVE,
            segment_metadata_flag=SegmentMetadataFlag.NOT_PRESENT,
            pdu_data_field_len=0,
            pdu_conf=empty_conf
        )

    @classmethod
    def unpack(cls, raw_packet: bytes) -> PduHeader:
        """Unpack a raw bytearray into the PDU header object representation

        :param raw_packet:
        :raise ValueError: Passed bytearray is too short.
        :return:
        """
        if len(raw_packet) < cls.FIXED_LENGTH:
            logger = get_console_logger()
            logger.warning('Can not unpack less than four bytes into PDU header')
            raise ValueError
        pdu_header = cls.__empty()
        pdu_header.pdu_type = (raw_packet[0] & 0x10) >> 4
        pdu_header.direction = (raw_packet[0] & 0x08) >> 3
        pdu_header.trans_mode = (raw_packet[0] & 0x04) >> 2
        pdu_header.crc_flag = (raw_packet[0] & 0x02) >> 1
        pdu_header.file_size = raw_packet[0] & 0x01
        pdu_header.pdu_data_field_len = raw_packet[1] << 8 | raw_packet[2]
        pdu_header.segmentation_control = SegmentationControl((raw_packet[3] & 0x80) >> 7)
        pdu_header.len_entity_id = cls.check_len_in_bytes((raw_packet[3] & 0x70) >> 4)
        pdu_header.segment_metadata_flag = SegmentMetadataFlag((raw_packet[3] & 0x08) >> 3)
        pdu_header.len_transaction_seq_num = cls.check_len_in_bytes(raw_packet[3] & 0x07)
        expected_remaining_len = 2 * pdu_header.len_entity_id + pdu_header.len_transaction_seq_num
        if len(raw_packet) - cls.FIXED_LENGTH < expected_remaining_len:
            logger = get_console_logger()
            logger.warning('Raw packet too small for PDU header')
            raise ValueError
        current_idx = 4
        source_entity_id = \
            raw_packet[current_idx: current_idx + pdu_header.len_entity_id]
        current_idx += pdu_header.len_entity_id
        pdu_header.transaction_seq_num = \
            raw_packet[current_idx: current_idx + pdu_header.len_transaction_seq_num]
        current_idx += pdu_header.len_transaction_seq_num
        dest_entity_id = \
            raw_packet[current_idx: current_idx + pdu_header.len_entity_id]
        pdu_header.set_entity_ids(source_entity_id=source_entity_id, dest_entity_id=dest_entity_id)
        return pdu_header

    @staticmethod
    def check_len_in_bytes(detected_len: int) -> LenInBytes:
        try:
            len_in_bytes = LenInBytes(detected_len)
        except ValueError:
            logger = get_console_logger()
            logger.warning(
                'Unsupported length field detected. '
                'Only 1, 2, 4 and 8 bytes are supported'
            )
            raise ValueError
        return len_in_bytes


class HasPduHeader:
    """Encapsulate common functions for classes which have a PDU header"""
    def __init__(self, pdu_header: PduHeader):
        self.pdu_header = pdu_header

    @property
    def file_size(self):
        return self.pdu_header.file_size

    @file_size.setter
    def file_size(self, file_size: FileSize):
        self.pdu_header.file_size = file_size

    @property
    def source_entity_id(self):
        return self.pdu_header.source_entity_id

    @property
    def dest_entity_id(self):
        return self.pdu_header.dest_entity_id

    @property
    def packet_len(self):
        return self.pdu_header.pdu_len

    @property
    def crc_flag(self):
        return self.pdu_header.crc_flag

    @crc_flag.setter
    def crc_flag(self, crc_flag: CrcFlag):
        self.pdu_header.crc_flag = crc_flag
