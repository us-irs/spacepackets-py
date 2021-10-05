from __future__ import annotations
import enum
import struct

from spacepackets.log import get_console_logger
from spacepackets.cfdp.definitions import LenInBytes, FileSize
from spacepackets.cfdp.conf import get_default_pdu_crc_mode, get_default_file_size, get_entity_ids


class PduType(enum.IntEnum):
    FILE_DIRECTIVE = 0
    FILE_DATA = 1


class Direction(enum.IntEnum):
    TOWARDS_RECEIVER = 0
    TOWARDS_SENDER = 1


class TransmissionModes(enum.IntEnum):
    ACKNOWLEDGED = 0
    UNACKNOWLEDGED = 1


class CrcFlag(enum.IntEnum):
    NO_CRC = 0
    WITH_CRC = 1
    GLOBAL_CONFIG = 2


class SegmentMetadataFlag(enum.IntEnum):
    """Aways 0 and ignored for File Directive PDUs (CCSDS 727.0-B-5 p.75)"""
    NOT_PRESENT = 0
    PRESENT = 1


class SegmentationControl(enum.IntEnum):
    """Always 0 and ignored for File Directive PDUs (CCSDS 727.0-B-5 p.75)"""
    NO_RECORD_BOUNDARIES_PRESERVATION = 0
    RECORD_BOUNDARIES_PRESERVATION = 1


class PduHeader:
    """This class encapsulates the fixed-format PDU header.
    For more, information, refer to CCSDS 727.0-B-5 p.75"""
    VERSION_BITS = 0b0010_0000
    FIXED_LENGTH = 4

    def __init__(
            self,
            pdu_type: PduType,
            trans_mode: TransmissionModes,
            segment_metadata_flag: SegmentMetadataFlag,
            transaction_seq_num: bytes,
            data_field_length: int = 0,
            large_file: FileSize = FileSize.GLOBAL_CONFIG,
            direction: Direction = Direction.TOWARDS_RECEIVER,
            source_entity_id: bytes = bytes(),
            dest_entity_id: bytes = bytes(),
            crc_flag: CrcFlag = CrcFlag.GLOBAL_CONFIG,
            seg_ctrl: SegmentationControl = SegmentationControl.NO_RECORD_BOUNDARIES_PRESERVATION,
    ):
        """Constructor for PDU header

        :param pdu_type:
        :param direction:
        :param trans_mode:
        :param segment_metadata_flag:
        :param transaction_seq_num:
        :param source_entity_id: If an empty bytearray is passed, the configured default value
            in the CFDP conf module will be used
        :param dest_entity_id: If an empty bytearray is passed, the configured default value
            in the CFDP conf module will be used
        :param crc_flag: If not supplied, assign the default configuration
        :param seg_ctrl:
        :raise ValueError: If some field are invalid or default values were unset
        """
        self.pdu_type = pdu_type
        self.direction = direction
        self.trans_mode = trans_mode
        self.pdu_data_field_length = data_field_length
        self.segmentation_control = seg_ctrl

        self.source_entity_id = source_entity_id
        self.dest_entity_id = dest_entity_id
        self.len_entity_id = 0
        self.set_entity_ids(source_entity_id=source_entity_id, dest_entity_id=dest_entity_id)

        self.transaction_seq_num = transaction_seq_num
        self.len_transaction_seq_num = 0
        self.set_transaction_seq_num(transaction_seq_num=transaction_seq_num)

        self.large_file = large_file
        self.set_file_size(file_size=self.large_file)
        self.crc_flag = crc_flag
        self.set_crc_flag(crc_flag=crc_flag)

        self.segment_metadata_flag = segment_metadata_flag

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
        self.source_entity_id = source_entity_id
        self.dest_entity_id = dest_entity_id
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

    def set_transaction_seq_num(self, transaction_seq_num: bytes):
        if transaction_seq_num is not None:
            try:
                self.len_transaction_seq_num = self.check_len_in_bytes(len(transaction_seq_num))
            except ValueError:
                logger = get_console_logger()
                logger.warning('Invalid length of transaction sequence number passed')
                raise ValueError
        self.transaction_seq_num = transaction_seq_num

    def set_file_size(self, file_size: FileSize):
        if file_size == FileSize.GLOBAL_CONFIG:
            self.large_file = get_default_file_size()
        else:
            self.large_file = file_size

    def set_crc_flag(self, crc_flag: CrcFlag):
        if crc_flag == CrcFlag.GLOBAL_CONFIG:
            self.crc_flag = get_default_pdu_crc_mode()
        else:
            self.crc_flag = crc_flag

    def set_pdu_data_field_length(self, new_length: int):
        """Set tHE PDU data field length
        :param new_length:
        :raises ValueError: Value too large
        :return:
        """
        if new_length > pow(2, 16) - 1:
            raise ValueError
        self.pdu_data_field_length = new_length

    def get_packet_len(self) -> int:
        """Get length of PDU header when packing it"""
        return self.FIXED_LENGTH + 2 * self.len_entity_id + self.len_transaction_seq_num

    def pack(self) -> bytearray:
        header = bytearray()
        header.append(
            self.VERSION_BITS | (self.pdu_type << 4) | (self.direction << 3) |
            (self.trans_mode << 2) | (self.crc_flag << 1) | self.large_file
        )
        header.append((self.pdu_data_field_length >> 8) & 0xff)
        header.append(self.pdu_data_field_length & 0xff)
        header.append(
            self.segmentation_control << 7 | self.len_entity_id << 4 |
            self.segment_metadata_flag << 3 | self.len_transaction_seq_num
        )
        header.extend(self.source_entity_id)
        header.extend(self.transaction_seq_num)
        header.extend(self.dest_entity_id)
        return header

    @classmethod
    def __empty(cls) -> PduHeader:
        return cls(
            pdu_type=PduType.FILE_DIRECTIVE,
            trans_mode=TransmissionModes.UNACKNOWLEDGED,
            source_entity_id=bytes([0]),
            dest_entity_id=bytes([0]),
            segment_metadata_flag=SegmentMetadataFlag.NOT_PRESENT,
            transaction_seq_num=bytes([0])
        )

    @classmethod
    def unpack(cls, raw_packet: bytearray) -> PduHeader:
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
        pdu_header.large_file = raw_packet[0] & 0x01
        pdu_header.pdu_data_field_length = raw_packet[1] << 8 | raw_packet[2]
        pdu_header.segmentation_control = (raw_packet[3] & 0x80) >> 7
        pdu_header.len_entity_id = cls.check_len_in_bytes((raw_packet[3] & 0x70) >> 4)
        pdu_header.segment_metadata_flag = (raw_packet[3] & 0x08) >> 3
        pdu_header.len_transaction_seq_num = cls.check_len_in_bytes(raw_packet[3] & 0x07)
        expected_remaining_len = 2 * pdu_header.len_entity_id + pdu_header.len_transaction_seq_num
        if len(raw_packet) - cls.FIXED_LENGTH < expected_remaining_len:
            logger = get_console_logger()
            logger.warning('Raw packet too small for PDU header')
            raise ValueError
        current_idx = 4
        pdu_header.source_entity_id = \
            raw_packet[current_idx: current_idx + pdu_header.len_entity_id]
        current_idx += pdu_header.len_entity_id
        pdu_header.transaction_seq_num = \
            raw_packet[current_idx: current_idx + pdu_header.len_transaction_seq_num]
        current_idx += pdu_header.len_transaction_seq_num
        pdu_header.dest_entity_id = \
            raw_packet[current_idx: current_idx + pdu_header.len_entity_id]
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
