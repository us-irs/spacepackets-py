from __future__ import annotations

import dataclasses
import struct
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Tuple, Optional, Type, List, Any, cast
import enum
from spacepackets.cfdp.lv import CfdpLv
from spacepackets.cfdp.defs import (
    ConditionCode,
    FaultHandlerCode,
    DeliveryCode,
    FileStatus,
    TransactionId,
    TransmissionMode,
)
from spacepackets.exceptions import BytesTooShortError
from spacepackets.util import UnsignedByteField


class TlvType(enum.IntEnum):
    """All available TLV types"""

    FILESTORE_REQUEST = 0x00
    FILESTORE_RESPONSE = 0x01
    MESSAGE_TO_USER = 0x02
    FAULT_HANDLER = 0x04
    FLOW_LABEL = 0x05
    ENTITY_ID = 0x06


class FilestoreActionCode(enum.IntEnum):
    """All filestore action codes as specified in CCSDS 727.0-B-5 p.86
    SNP: Second name present, SNN: Second name not present"""

    CREATE_FILE_SNM = 0b0000
    DELETE_FILE_SNN = 0b0001
    RENAME_FILE_SNP = 0b0010
    APPEND_FILE_SNP = 0b0011
    REPLACE_FILE_SNP = 0b0100
    CREATE_DIR_SNN = 0b0101
    REMOVE_DIR_SNN = 0b0110
    DENY_FILE_SMM = 0b0111
    DENY_DIR_SNN = 0b1000


class FilestoreResponseStatusCode(enum.IntEnum):
    """File store response status codes. First four bits are the action code, last four bits
    the status code"""

    SUCCESS = 0b0000
    NOT_PERFORMED = 0b1111
    APPEND_FROM_DATA_FILE_NOT_EXISTS = 0b0010

    CREATE_SUCCESS = FilestoreActionCode.CREATE_FILE_SNM << 4 | SUCCESS
    CREATE_NOT_ALLOWED = FilestoreActionCode.CREATE_FILE_SNM << 4 | 0b0001
    CREATE_NOT_PERFORMED = FilestoreActionCode.CREATE_FILE_SNM << 4 | NOT_PERFORMED

    DELETE_SUCCESS = FilestoreActionCode.DELETE_FILE_SNN << 4 | SUCCESS
    DELETE_FILE_DOES_NOT_EXIST = FilestoreActionCode.DELETE_FILE_SNN << 4 | 0b0001
    DELETE_NOT_ALLOWED = FilestoreActionCode.DELETE_FILE_SNN << 4 | NOT_PERFORMED

    RENAME_SUCCESS = FilestoreActionCode.RENAME_FILE_SNP << 4 | SUCCESS
    RENAME_OLD_FILE_DOES_NOT_EXIST = FilestoreActionCode.RENAME_FILE_SNP << 4 | 0b0001
    RENAME_NEW_FILE_DOES_EXIST = FilestoreActionCode.RENAME_FILE_SNP << 4 | 0b0010
    RENAME_NOT_ALLOWED = FilestoreActionCode.RENAME_FILE_SNP << 4 | 0b0011
    RENAME_NOT_PERFORMED = FilestoreActionCode.RENAME_FILE_SNP << 4 | NOT_PERFORMED

    APPEND_SUCCESS = FilestoreActionCode.APPEND_FILE_SNP << 4 | SUCCESS
    # Name of file whose contents form the first part of the new file and name of the new file
    APPEND_FILE_NAME_ONE_NOT_EXISTS = FilestoreActionCode.APPEND_FILE_SNP << 4 | 0b0001
    # Name of the file whose contents will form the second part of the new file
    APPEND_FILE_NAME_TWO_NOT_EXISTS = FilestoreActionCode.APPEND_FILE_SNP << 4 | 0b0010
    APPEND_NOT_ALLOWED = FilestoreActionCode.APPEND_FILE_SNP << 4 | 0b0011
    APPEND_NOT_PERFORMED = FilestoreActionCode.APPEND_FILE_SNP << 4 | NOT_PERFORMED

    REPLACE_SUCCESS = FilestoreActionCode.REPLACE_FILE_SNP << 4 | SUCCESS
    # File name
    REPLACE_FILE_NAME_ONE_TO_BE_REPLACED_DOES_NOT_EXIST = (
        FilestoreActionCode.REPLACE_FILE_SNP << 4 | 0b0001
    )
    REPLACE_FILE_NAME_TWO_REPLACE_SOURCE_NOT_EXIST = (
        FilestoreActionCode.REPLACE_FILE_SNP << 4 | 0b0010
    )
    REPLACE_NOT_ALLOWED = FilestoreActionCode.REPLACE_FILE_SNP << 4 | 0b0011
    REPLACE_NOT_PERFORMED = FilestoreActionCode.REPLACE_FILE_SNP << 4 | NOT_PERFORMED

    CREATE_DIR_SUCCESS = FilestoreActionCode.CREATE_DIR_SNN << 4 | SUCCESS
    CREATE_DIR_CAN_NOT_BE_CREATED = FilestoreActionCode.CREATE_DIR_SNN << 4 | 0b0001
    CREATE_DIR_NOT_PERFORMED = FilestoreActionCode.CREATE_DIR_SNN << 4 | NOT_PERFORMED

    REMOVE_DIR_SUCCESS = FilestoreActionCode.REMOVE_DIR_SNN << 4 | SUCCESS
    REMOVE_DIR_DOES_NOT_EXIST = FilestoreActionCode.REMOVE_DIR_SNN << 4 | 0b0001
    REMOVE_DIR_NOT_ALLOWED = FilestoreActionCode.REMOVE_DIR_SNN << 4 | 0b0010
    REMOVE_DIR_NOT_PERFORMED = FilestoreActionCode.REMOVE_DIR_SNN << 4 | NOT_PERFORMED

    DENY_FILE_DEL_SUCCESS = FilestoreActionCode.DENY_FILE_SMM << 4 | SUCCESS
    DENY_FILE_DEL_NOT_ALLOWED = FilestoreActionCode.DENY_FILE_SMM << 4 | 0b0010
    DENY_FILE_DEL_NOT_PERFORMED = FilestoreActionCode.DENY_FILE_SMM << 4 | NOT_PERFORMED

    DENY_DIR_DEL_SUCCESS = FilestoreActionCode.DENY_DIR_SNN << 4 | SUCCESS
    DENY_DIR_DEL_NOT_ALLOWED = FilestoreActionCode.DENY_DIR_SNN << 4 | 0b0010
    DENY_DIR_DEL_NOT_PERFORMED = FilestoreActionCode.DENY_DIR_SNN << 4 | NOT_PERFORMED
    INVALID = -1


def map_enum_status_code_to_int(status_code: FilestoreResponseStatusCode) -> int:
    return status_code & 0x0F


def map_enum_status_code_to_action_status_code(
    status_code_enum: FilestoreResponseStatusCode,
) -> Tuple[FilestoreActionCode, int]:
    """Map a given file store response status code to the action code and the corresponding
    4 bit status code. the status code will be 0x00 for a SUCCESS operation and 0b1111 if the
    operation was not performed.

    :raise ValueError: Invalid filestore action code detected.
    """
    return FilestoreActionCode((status_code_enum & 0xF0) >> 4), status_code_enum & 0x0F


def map_int_status_code_to_enum(
    action_code: FilestoreActionCode, status_code: int
) -> FilestoreResponseStatusCode:
    """Maps an action code and the status code of a filestore response to the status code.

    :param action_code:
    :param status_code:
    :return: The status code. Will be FilestoreResponseStatusCode.INVALID in case no valid status
        code was detected
    """
    try:
        status_code = FilestoreResponseStatusCode(action_code << 4 | status_code)
        return status_code
    except (IndexError, ValueError):
        return FilestoreResponseStatusCode.INVALID


class TlvTypeMissmatch(Exception):
    def __init__(self, found: TlvType, expected: TlvType):
        self.found = found
        self.expected = expected
        super().__init__(f"Expected TLV {self.expected}, found {self.found}")


class AbstractTlvBase(ABC):
    @abstractmethod
    def pack(self) -> bytearray:
        pass

    @property
    @abstractmethod
    def packet_len(self) -> int:
        pass

    @property
    @abstractmethod
    def tlv_type(self) -> TlvType:
        pass

    @property
    @abstractmethod
    def value(self) -> bytes:
        pass

    def __eq__(self, other: AbstractTlvBase):
        return self.tlv_type == other.tlv_type and self.value == other.value

    def check_type(self, tlv_type: TlvType):
        if self.tlv_type != tlv_type:
            raise TlvTypeMissmatch(found=tlv_type, expected=self.tlv_type)


class CfdpTlv(AbstractTlvBase):
    """Encapsulates the CFDP Type-Length-Value (TLV) format.
    For more information, refer to CCSDS 727.0-B-5 p.77
    """

    MINIMAL_LEN = 2

    def __init__(self, tlv_type: TlvType, value: bytes):
        """Constructor for TLV field.

        Raises
        -------

        ValueError
            Length invalid or value length not equal to specified length.
        """
        self.value_len = len(value)
        if self.value_len > pow(2, 8) - 1:
            raise ValueError("Length larger than allowed 255 bytes")
        self._tlv_type = tlv_type
        self._value = value

    @property
    def tlv_type(self):
        return self._tlv_type

    @tlv_type.setter
    def tlv_type(self, tlv_type: TlvType):
        self._tlv_type = tlv_type

    @property
    def value(self) -> bytes:
        return self._value

    def pack(self) -> bytearray:
        tlv_data = bytearray()
        tlv_data.append(self.tlv_type)
        tlv_data.append(self.value_len)
        tlv_data.extend(self._value)
        return tlv_data

    @classmethod
    def unpack(cls, data: bytes) -> CfdpTlv:
        """Parses LV field at the start of the given bytearray

        :param data:
        :raise BytesTooShortError: Length of raw data too short.
        :raise ValueError: Invalid format of the raw bytearray or type field invalid
        :return:
        """
        if len(data) < 2:
            raise BytesTooShortError(2, len(data))
        try:
            tlv_type = TlvType(data[0])
        except ValueError:
            raise ValueError(
                f"TLV field invalid, found value {data[0]} is not a possible TLV"
                " parameter"
            )

        value = bytearray()
        if len(data) > 2:
            length = data[1]
            if 2 + length > len(data):
                raise BytesTooShortError(length + 2, len(data))
            value.extend(data[2 : 2 + length])
        return cls(tlv_type=tlv_type, value=value)

    @property
    def packet_len(self) -> int:
        return self.MINIMAL_LEN + len(self._value)

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(tlv_type={self.tlv_type!r},"
            f" value={self.value!r})"
        )

    def __str__(self):
        return (
            f"CFDP TLV with type {self.tlv_type} and data"
            f" 0x[{self._value.hex(sep=',')}] with length {len(self._value)}"
        )


class EntityIdTlv(AbstractTlvBase):
    TLV_TYPE = TlvType.ENTITY_ID

    def __init__(self, entity_id: bytes):
        self.tlv = CfdpTlv(tlv_type=TlvType.ENTITY_ID, value=entity_id)

    def pack(self) -> bytearray:
        return self.tlv.pack()

    @property
    def packet_len(self):
        return self.tlv.packet_len

    @property
    def tlv_type(self) -> TlvType:
        return EntityIdTlv.TLV_TYPE

    @property
    def value(self) -> bytes:
        return self.tlv.value

    @classmethod
    def __empty(cls) -> EntityIdTlv:
        return cls(entity_id=bytes())

    @classmethod
    def unpack(cls, data: bytes) -> EntityIdTlv:
        entity_id_tlv = cls.__empty()
        entity_id_tlv.tlv = CfdpTlv.unpack(data=data)
        entity_id_tlv.check_type(tlv_type=TlvType.ENTITY_ID)
        return entity_id_tlv

    @classmethod
    def from_tlv(cls, cfdp_tlv: CfdpTlv) -> EntityIdTlv:
        if cfdp_tlv.tlv_type != cls.TLV_TYPE:
            raise TlvTypeMissmatch(cfdp_tlv.tlv_type, cls.TLV_TYPE)
        entity_id_tlv = cls.__empty()
        entity_id_tlv.tlv = cfdp_tlv
        return entity_id_tlv


class FaultHandlerOverrideTlv(AbstractTlvBase):
    TLV_TYPE = TlvType.FAULT_HANDLER

    def __init__(
        self,
        condition_code: ConditionCode,
        handler_code: FaultHandlerCode,
    ):
        self.condition_code = condition_code
        self.handler_code = handler_code
        self.tlv = CfdpTlv(
            tlv_type=self.tlv_type,
            value=bytes([self.condition_code << 4 | self.handler_code]),
        )

    def pack(self) -> bytearray:
        return self.tlv.pack()

    @property
    def packet_len(self):
        return self.tlv.packet_len

    @property
    def value(self) -> bytes:
        return self.tlv.value

    @property
    def tlv_type(self) -> TlvType:
        return FaultHandlerOverrideTlv.TLV_TYPE

    @classmethod
    def __empty(cls) -> FaultHandlerOverrideTlv:
        return cls(
            condition_code=ConditionCode.NO_ERROR,
            handler_code=FaultHandlerCode.IGNORE_ERROR,
        )

    @classmethod
    def unpack(cls, data: bytes) -> FaultHandlerOverrideTlv:
        fault_handler_ovr_tlv = cls.__empty()
        fault_handler_ovr_tlv.tlv = CfdpTlv.unpack(data=data)
        fault_handler_ovr_tlv.check_type(tlv_type=FaultHandlerOverrideTlv.TLV_TYPE)
        fault_handler_ovr_tlv.condition_code = (
            fault_handler_ovr_tlv.tlv.value[0] & 0xF0
        ) >> 4
        fault_handler_ovr_tlv.handler_code = fault_handler_ovr_tlv.tlv.value[0] & 0x0F
        return fault_handler_ovr_tlv

    @classmethod
    def from_tlv(cls, cfdp_tlv: CfdpTlv) -> FaultHandlerOverrideTlv:
        if cfdp_tlv.tlv_type != cls.TLV_TYPE:
            raise TlvTypeMissmatch(cfdp_tlv.tlv_type, cls.TLV_TYPE)
        fault_handler_tlv = cls.__empty()
        fault_handler_tlv.tlv = cfdp_tlv
        fault_handler_tlv.condition_code = (cfdp_tlv.value[0] >> 4) & 0x0F
        fault_handler_tlv.handler_code = cfdp_tlv.value[0] & 0x0F
        return fault_handler_tlv


def create_cfdp_proxy_and_dir_op_message_marker() -> bytes:
    """CCSDS 727.0-B-5 p.88: The message identifier for standard CFDP proxy and dir op messages
    is the presence of the ASCII characters 'cfdp' in the first four octests of each message"""
    return "cfdp".encode()


class MessageToUserTlv(AbstractTlvBase):
    """Message to User TLV implementation as specified in CCSDS 727.0-B-5 5.4.3"""

    TLV_TYPE = TlvType.MESSAGE_TO_USER

    def __init__(self, msg: bytes):
        self.tlv = CfdpTlv(tlv_type=MessageToUserTlv.TLV_TYPE, value=msg)

    def pack(self) -> bytearray:
        return self.tlv.pack()

    @property
    def packet_len(self):
        return self.tlv.packet_len

    @property
    def value(self) -> bytes:
        return self.tlv.value

    @property
    def tlv_type(self) -> TlvType:
        return MessageToUserTlv.TLV_TYPE

    def is_reserved_cfdp_message(self) -> bool:
        if len(self.tlv.value) >= 5 and self.tlv.value[0:4].decode() == "cfdp":
            return True
        return False

    def to_reserved_msg_tlv(self) -> Optional[ReservedCfdpMessage]:
        """Attempt to convert to a reserved CFDP message. Please note that this operation
        will fail if the message if not a reserved CFDP message and will then return None.
        This method is especially useful to have access to the more specialized
        :py:class:`ReservedCfdpMessage` API."""
        if not self.is_reserved_cfdp_message():
            return None
        return ReservedCfdpMessage(self.tlv.value[4], self.tlv.value[5:])

    @classmethod
    def __empty(cls):
        return cls(bytes())

    @classmethod
    def unpack(cls, data: bytes) -> MessageToUserTlv:
        msg_to_user_tlv = cls.__empty()
        msg_to_user_tlv.tlv = CfdpTlv.unpack(data)
        msg_to_user_tlv.check_type(MessageToUserTlv.TLV_TYPE)
        return msg_to_user_tlv

    @classmethod
    def from_tlv(cls, cfdp_tlv: CfdpTlv) -> MessageToUserTlv:
        if cfdp_tlv.tlv_type != cls.TLV_TYPE:
            raise TlvTypeMissmatch(cfdp_tlv.tlv_type, cls.TLV_TYPE)
        msg_to_user_tlv = cls.__empty()
        msg_to_user_tlv.tlv = cfdp_tlv
        return msg_to_user_tlv


class FlowLabelTlv(AbstractTlvBase):
    TLV_TYPE = TlvType.FLOW_LABEL

    def __init__(self, flow_label: bytes):
        self.tlv = CfdpTlv(tlv_type=self.tlv_type, value=flow_label)

    @classmethod
    def __empty(cls):
        return cls(bytes())

    def pack(self) -> bytearray:
        return self.tlv.pack()

    @property
    def packet_len(self):
        return self.tlv.packet_len

    @property
    def value(self) -> bytes:
        return self.tlv.value

    @property
    def tlv_type(self) -> TlvType:
        return FlowLabelTlv.TLV_TYPE

    @classmethod
    def unpack(cls, data: bytes) -> FlowLabelTlv:
        flow_label_tlv = cls.__empty()
        tlv = CfdpTlv.unpack(data=data)
        if tlv.tlv_type != FlowLabelTlv.TLV_TYPE:
            raise TlvTypeMissmatch(tlv.tlv_type, cls.TLV_TYPE)
        flow_label_tlv.tlv = tlv
        return flow_label_tlv

    @classmethod
    def from_tlv(cls, cfdp_tlv: CfdpTlv) -> FlowLabelTlv:
        if cfdp_tlv.tlv_type != FlowLabelTlv.TLV_TYPE:
            raise TlvTypeMissmatch(cfdp_tlv.tlv_type, cls.TLV_TYPE)
        flow_label_tlv = cls.__empty()
        flow_label_tlv.tlv = cfdp_tlv
        return flow_label_tlv


class FileStoreRequestBase:
    def __init__(
        self,
        action_code: FilestoreActionCode,
        first_file_name: str,
        second_file_name: str,
    ):
        self.action_code = action_code
        self.first_file_name = first_file_name
        self.second_file_name = second_file_name
        self.tlv: Optional[CfdpTlv] = None

    def _common_packer(self, status_code: int) -> bytearray:
        tlv_value = bytearray()
        tlv_value.append(self.action_code << 4 | status_code)
        first_name_lv = CfdpLv(value=self.first_file_name.encode())
        tlv_value.extend(first_name_lv.pack())
        if self.action_code in [
            FilestoreActionCode.REPLACE_FILE_SNP,
            FilestoreActionCode.RENAME_FILE_SNP,
            FilestoreActionCode.APPEND_FILE_SNP,
        ]:
            second_name_lv = CfdpLv(value=self.second_file_name.encode())
            tlv_value.extend(second_name_lv.pack())
        return tlv_value

    def common_packet_len(self) -> int:
        # 2 bytes TLV header, 1 byte action code and status code, first file name LV length
        expected_len = 3 + len(self.first_file_name) + 1
        if self.action_code in [
            FilestoreActionCode.REPLACE_FILE_SNP,
            FilestoreActionCode.RENAME_FILE_SNP,
            FilestoreActionCode.APPEND_FILE_SNP,
        ]:
            expected_len += len(self.second_file_name) + 1
        return expected_len

    @staticmethod
    def _check_raw_tlv_field(first_byte: int, expected: TlvType):
        try:
            raw_tlv_type = TlvType(first_byte)
            if raw_tlv_type != expected:
                raise TlvTypeMissmatch(raw_tlv_type, expected)
        except IndexError:
            raise ValueError(f"No TLV type for raw field {first_byte}")

    @staticmethod
    def _common_unpacker(
        raw_bytes: bytes,
    ) -> Tuple[FilestoreActionCode, str, int, int, Optional[str]]:
        """Does only unpack common fields, does not unpack the filestore message of a Filestore
        Response package

        :return Tuple where the first value is the enumerate Action code, the second value
            is the first file name, the second value is the status code as an integer,
            the third value is the length of the full TLV packet
        """
        value_idx = 0
        action_code_as_int = (raw_bytes[value_idx] >> 4) & 0x0F
        try:
            action_code = FilestoreActionCode(action_code_as_int)
        except ValueError:
            raise ValueError(
                "Invalid action code in file store response with value"
                f" {action_code_as_int}"
            )
        status_code_as_int = raw_bytes[value_idx] & 0x0F
        value_idx += 1
        first_lv = CfdpLv.unpack(raw_bytes=raw_bytes[value_idx:])
        value_idx += first_lv.packet_len
        first_file_name = first_lv.value.decode()
        if action_code in [
            FilestoreActionCode.REPLACE_FILE_SNP,
            FilestoreActionCode.RENAME_FILE_SNP,
            FilestoreActionCode.APPEND_FILE_SNP,
        ]:
            second_lv = CfdpLv.unpack(raw_bytes=raw_bytes[value_idx:])
            value_idx += second_lv.packet_len
            second_file_name = second_lv.value.decode()
        else:
            second_file_name = None
        return (
            action_code,
            first_file_name,
            status_code_as_int,
            value_idx,
            second_file_name,
        )


class FileStoreRequestTlv(FileStoreRequestBase, AbstractTlvBase):
    TLV_TYPE = TlvType.FILESTORE_REQUEST

    def __init__(
        self,
        action_code: FilestoreActionCode,
        first_file_name: str,
        second_file_name: str = "",
    ):
        super().__init__(
            action_code=action_code,
            first_file_name=first_file_name,
            second_file_name=second_file_name,
        )

    def generate_tlv(self):
        if self.tlv is None:
            self.tlv = self._build_tlv()

    def pack(self) -> bytearray:
        self.generate_tlv()
        return self.tlv.pack()

    @property
    def packet_len(self):
        return self.common_packet_len()

    @property
    def value(self) -> bytes:
        self.generate_tlv()
        return self.tlv.value

    @property
    def tlv_type(self) -> TlvType:
        return FileStoreRequestTlv.TLV_TYPE

    @classmethod
    def __empty(cls) -> FileStoreRequestTlv:
        return cls(
            action_code=FilestoreActionCode.CREATE_FILE_SNM,
            first_file_name="",
            second_file_name="",
        )

    def _build_tlv(self) -> CfdpTlv:
        tlv_value = self._common_packer(status_code=0b0000)
        return CfdpTlv(tlv_type=TlvType.FILESTORE_REQUEST, value=tlv_value)

    @classmethod
    def unpack(cls, data: bytes) -> FileStoreRequestTlv:
        cls._check_raw_tlv_field(data[0], FileStoreRequestTlv.TLV_TYPE)
        filestore_req = cls.__empty()
        cls._set_fields(filestore_req, data[2:])
        return filestore_req

    @classmethod
    def from_tlv(cls, cfdp_tlv: CfdpTlv) -> FileStoreRequestTlv:
        if cfdp_tlv.tlv_type != cls.TLV_TYPE:
            raise TlvTypeMissmatch(cfdp_tlv.tlv_type, cls.TLV_TYPE)
        fs_response = cls.__empty()
        cls._set_fields(fs_response, cfdp_tlv.value)
        return fs_response

    @classmethod
    def _set_fields(cls, instance: FileStoreRequestTlv, raw_data: bytes):
        action_code, first_name, _, _, second_name = cls._common_unpacker(
            raw_bytes=raw_data
        )
        instance.action_code = action_code
        instance.first_file_name = first_name
        if second_name is not None:
            instance.second_file_name = second_name
        return instance


class FileStoreResponseTlv(FileStoreRequestBase, AbstractTlvBase):
    TLV_TYPE = TlvType.FILESTORE_RESPONSE

    def __init__(
        self,
        action_code: FilestoreActionCode,
        status_code: FilestoreResponseStatusCode,
        first_file_name: str,
        second_file_name: str = "",
        filestore_msg: CfdpLv = CfdpLv(value=bytes()),
    ):
        super().__init__(
            action_code=action_code,
            first_file_name=first_file_name,
            second_file_name=second_file_name,
        )
        self.status_code = status_code
        self.filestore_msg = filestore_msg

    def generate_tlv(self):
        if self.tlv is None:
            self.tlv = self._build_tlv()

    def pack(self) -> bytearray:
        self.generate_tlv()
        return self.tlv.pack()  # type: ignore

    @property
    def value(self) -> bytes:
        self.generate_tlv()
        return self.tlv.value  # type: ignore

    @property
    def packet_len(self):
        return self.common_packet_len() + self.filestore_msg.packet_len

    @property
    def tlv_type(self) -> TlvType:
        return FileStoreResponseTlv.TLV_TYPE

    @classmethod
    def __empty(cls) -> FileStoreResponseTlv:
        return cls(
            action_code=FilestoreActionCode.CREATE_FILE_SNM,
            status_code=FilestoreResponseStatusCode.CREATE_SUCCESS,
            first_file_name="",
            second_file_name="",
        )

    def _build_tlv(self) -> CfdpTlv:
        status_code_as_int = map_enum_status_code_to_int(status_code=self.status_code)
        tlv_value = self._common_packer(status_code=status_code_as_int)
        tlv_value.extend(self.filestore_msg.pack())
        return CfdpTlv(tlv_type=TlvType.FILESTORE_RESPONSE, value=tlv_value)

    @classmethod
    def unpack(cls, data: bytes) -> FileStoreResponseTlv:
        cls._check_raw_tlv_field(data[0], FileStoreResponseTlv.TLV_TYPE)
        filestore_reply = cls.__empty()
        cls._set_fields(filestore_reply, data[2:])
        return filestore_reply

    @classmethod
    def from_tlv(cls, cfdp_tlv: CfdpTlv) -> FileStoreResponseTlv:
        if cfdp_tlv.tlv_type != cls.TLV_TYPE:
            raise TlvTypeMissmatch(cfdp_tlv.tlv_type, cls.TLV_TYPE)
        fs_response = FileStoreResponseTlv.__empty()
        cls._set_fields(fs_response, cfdp_tlv.value)
        return fs_response

    @classmethod
    def _set_fields(cls, instance: FileStoreResponseTlv, data: bytes):
        action_code, first_name, status_code, idx, second_name = cls._common_unpacker(
            raw_bytes=data
        )
        instance.action_code = action_code
        instance.first_file_name = first_name
        try:
            status_code_named = FilestoreResponseStatusCode(
                action_code << 4 | status_code
            )
        except ValueError:
            raise ValueError(
                "Invalid status code in file store response with value"
                f" {status_code} for action code {action_code}"
            )
        instance.status_code = status_code_named
        if second_name is not None:
            instance.second_file_name = second_name
        instance.filestore_msg = CfdpLv.unpack(data[idx:])


TlvList = List[AbstractTlvBase]


class ProxyMessageType(enum.IntEnum):
    PUT_REQUEST = 0x00
    MSG_TO_USER = 0x01
    FS_REQUEST = 0x02
    FAULT_HANDLER_OVERRIDE = 0x03
    TRANSMISSION_MODE = 0x04
    FLOW_LABEL = 0x05
    SEGMENTATION_CTRL = 0x06
    PUT_RESPONSE = 0x07
    FS_RESPONSE = 0x08
    PUT_CANCEL = 0x09
    CLOSURE_REQUEST = 0x0B


ORIGINATING_TRANSACTION_ID_MSG_TYPE_ID = 0x0A


class DirectoryOperationMessageType(enum.IntEnum):
    LISTING_REQUEST = 0x10
    LISTING_RESPONSE = 0x11
    CUSTOM_LISTING_PARAMETERS = 0x15
    """Custom message type not specified by the standard. Used to supply parameters like the
    recursive and the all option to the directory listing."""


class ReservedCfdpMessage(AbstractTlvBase):
    """Reserved CFDP message implementation as specified in CCSDS 727.0-B-5 6.1.

    This class also exposes various helper types to extract the various reserved CFDP message
    type parameters. A common way to create an instance of this class from a raw bytestream is to
    create a :py:class:`spacepackets.cfdp.tlv.MessageToUserTlv` first after checking the TLV
    message type, and then use the
    :py:meth:`spacepackets.cfdp.tlv.MessageToUserTlv.is_reserved_cfdp_message`
    and :py:meth:`spacepackets.cfdp.tlv.MessageToUserTlv.to_reserved_msg_tlv` API for the
    conversion.
    """

    def __init__(self, msg_type: int, value: bytes):
        assert msg_type < pow(2, 8) - 1
        full_value = bytearray("cfdp".encode())
        full_value.append(msg_type)
        full_value.extend(value)
        self.tlv = CfdpTlv(TlvType.MESSAGE_TO_USER, full_value)

    def pack(self) -> bytearray:
        return self.tlv.pack()

    def to_generic_msg_to_user_tlv(self) -> MessageToUserTlv:
        """Can be used to convert the reserved CFDP message to the more generic superset.
        This is required for the metadata PDU API, which expects generic
        :py:class:`MessageToUserTlv` s"""
        return MessageToUserTlv.from_tlv(self.tlv)

    @property
    def packet_len(self):
        return self.tlv.packet_len

    @property
    def tlv_type(self) -> TlvType:
        return self.tlv.tlv_type

    @property
    def value(self) -> bytes:
        return self.tlv.value

    def get_reserved_cfdp_message_type(self) -> int:
        return self.tlv.value[4]

    def is_cfdp_proxy_operation(self) -> bool:
        try:
            ProxyMessageType(self.get_reserved_cfdp_message_type())
            return True
        except ValueError:
            return False

    def is_directory_operation(self) -> bool:
        try:
            DirectoryOperationMessageType(self.get_reserved_cfdp_message_type())
            return True
        except ValueError:
            return False

    def is_originating_transaction_id(self) -> bool:
        return (
            self.get_reserved_cfdp_message_type()
            == ORIGINATING_TRANSACTION_ID_MSG_TYPE_ID
        )

    def get_cfdp_proxy_message_type(self) -> Optional[ProxyMessageType]:
        if not self.is_cfdp_proxy_operation():
            return None
        return ProxyMessageType(self.get_reserved_cfdp_message_type())

    def get_directory_operation_type(self) -> Optional[DirectoryOperationMessageType]:
        if not self.is_directory_operation():
            return None
        return DirectoryOperationMessageType(self.get_reserved_cfdp_message_type())

    def get_originating_transaction_id(
        self,
    ) -> Optional[TransactionId]:
        if not self.is_originating_transaction_id():
            return None
        if len(self.value) < 1:
            raise ValueError("originating transaction ID value field to small")
        source_id_len = ((self.value[5] >> 4) & 0b111) + 1
        seq_num_len = (self.value[5] & 0b111) + 1
        current_idx = 6
        if len(self.value) < source_id_len + seq_num_len + 1:
            raise ValueError("originating transaction ID value field to small")
        source_id = self.value[current_idx : current_idx + source_id_len]
        current_idx += source_id_len
        seq_num = self.value[current_idx : current_idx + seq_num_len]
        return TransactionId(
            UnsignedByteField.from_bytes(source_id),
            UnsignedByteField.from_bytes(seq_num),
        )

    def get_proxy_put_request_params(self) -> Optional[ProxyPutRequestParams]:
        """This function extract the proxy put request parameters from the raw value if
        applicable. If the value format is invalid, this function will return None."""
        if (
            not self.is_cfdp_proxy_operation()
            or self.get_cfdp_proxy_message_type() != ProxyMessageType.PUT_REQUEST
        ):
            return None
        current_idx = 5
        dest_id_lv = CfdpLv.unpack(self.value[current_idx:])
        current_idx += dest_id_lv.packet_len
        if current_idx >= len(self.value):
            return None
        source_name_lv = CfdpLv.unpack(self.value[current_idx:])
        current_idx += source_name_lv.packet_len
        if current_idx >= len(self.value):
            return None
        dest_name_lv = CfdpLv.unpack(self.value[current_idx:])
        if len(dest_id_lv.value) == 1:
            dest_id = dest_id_lv.value[0]
        elif len(dest_id_lv.value) == 2:
            dest_id = struct.unpack("!H", dest_id_lv.value[0:2])[0]
        elif len(dest_id_lv.value) == 4:
            dest_id = struct.unpack("!I", dest_id_lv.value[0:4])[0]
        elif len(dest_id_lv.value) == 8:
            dest_id = struct.unpack("!Q", dest_id_lv.value[0:8])[0]
        else:
            return None
        return ProxyPutRequestParams(
            UnsignedByteField(dest_id, len(dest_id_lv.value)),
            source_name_lv,
            dest_name_lv,
        )

    def get_proxy_put_response_params(self) -> Optional[ProxyPutResponseParams]:
        if (
            not self.is_cfdp_proxy_operation()
            or self.get_cfdp_proxy_message_type() != ProxyMessageType.PUT_RESPONSE
        ):
            return None
        condition_code = (self.value[5] >> 4) & 0b1111
        delivery_code = (self.value[5] >> 2) & 0b1
        file_status = self.value[5] & 0b11
        return ProxyPutResponseParams(condition_code, delivery_code, file_status)

    def get_proxy_closure_requested(self) -> Optional[bool]:
        if (
            not self.is_cfdp_proxy_operation()
            or self.get_cfdp_proxy_message_type() != ProxyMessageType.CLOSURE_REQUEST
        ):
            return None
        return self.value[5] & 0b1

    def get_proxy_transmission_mode(self) -> Optional[TransmissionMode]:
        if (
            not self.is_cfdp_proxy_operation()
            or self.get_cfdp_proxy_message_type() != ProxyMessageType.TRANSMISSION_MODE
        ):
            return None
        return TransmissionMode(self.value[5] & 0b1)

    def get_dir_listing_request_params(self) -> Optional[DirectoryParams]:
        if (
            not self.is_directory_operation()
            or self.get_directory_operation_type()
            != DirectoryOperationMessageType.LISTING_REQUEST
        ):
            return None
        dir_path_lv = CfdpLv.unpack(self.value[5:])
        dir_file_name_lv = CfdpLv.unpack(self.value[5 + dir_path_lv.packet_len :])
        return DirectoryParams(dir_path_lv, dir_file_name_lv)

    def get_dir_listing_response_params(self) -> Optional[Tuple[bool, DirectoryParams]]:
        """
        Returns
        ---------
            None if this is not a directory listing response. Otherwise, returns a tuple where
            the first entry is a boolean denoting whether the directory listing response was
            generated succesfully, and the second entry being the directory listing parameters.
        """
        if (
            not self.is_directory_operation()
            or self.get_directory_operation_type()
            != DirectoryOperationMessageType.LISTING_RESPONSE
        ):
            return None
        if len(self.value) < 1:
            raise ValueError(
                f"value with length {len(self.value)} too small for dir listing response."
            )
        listing_success = bool((self.value[5] >> 7) & 0b1)
        dir_path_lv = CfdpLv.unpack(self.value[6:])
        dir_file_name_lv = CfdpLv.unpack(self.value[6 + dir_path_lv.packet_len :])
        return listing_success, DirectoryParams(dir_path_lv, dir_file_name_lv)

    def get_dir_listing_options(self) -> Optional[DirListingOptions]:
        if (
            not self.is_directory_operation()
            or self.get_directory_operation_type()
            != DirectoryOperationMessageType.CUSTOM_LISTING_PARAMETERS
        ):
            return None
        if len(self.value) < 1:
            raise ValueError(
                f"value with length {len(self.value)} too small for dir listing options."
            )
        return DirListingOptions((self.value[5] >> 1) & 0b1, self.value[5] & 0b1)


@dataclasses.dataclass
class ProxyPutRequestParams:
    dest_entity_id: UnsignedByteField
    source_file_name: CfdpLv
    dest_file_name: CfdpLv


class ProxyPutRequest(ReservedCfdpMessage):
    def __init__(self, params: ProxyPutRequestParams):
        value = CfdpLv(params.dest_entity_id.as_bytes).pack()
        value.extend(params.source_file_name.pack())
        value.extend(params.dest_file_name.pack())
        super().__init__(ProxyMessageType.PUT_REQUEST, value)


@dataclasses.dataclass
class ProxyPutResponseParams:
    condition_code: ConditionCode
    delivery_code: DeliveryCode
    file_status: FileStatus


class ProxyPutResponse(ReservedCfdpMessage):
    def __init__(self, params: ProxyPutResponseParams):
        super().__init__(
            ProxyMessageType.PUT_RESPONSE,
            bytes(
                [
                    (params.condition_code << 4)
                    | (params.delivery_code << 2)
                    | params.file_status
                ]
            ),
        )


class ProxyCancelRequest(ReservedCfdpMessage):
    def __init__(self):
        super().__init__(ProxyMessageType.PUT_CANCEL, bytes())


class ProxyClosureRequest(ReservedCfdpMessage):
    def __init__(self, closure_requested: bool):
        super().__init__(ProxyMessageType.CLOSURE_REQUEST, bytes([closure_requested]))


class ProxyTransmissionMode(ReservedCfdpMessage):
    def __init__(self, transmission_mode: TransmissionMode):
        super().__init__(ProxyMessageType.TRANSMISSION_MODE, bytes([transmission_mode]))


class OriginatingTransactionId(ReservedCfdpMessage):
    def __init__(self, transaction_id: TransactionId):
        if transaction_id.source_id.byte_len not in [
            1,
            2,
            4,
            8,
        ] or transaction_id.seq_num.byte_len not in [1, 2, 4, 8]:
            raise ValueError(
                "only byte length [1, 2, 4, 8] are allowed for the source ID or the transaction "
                "sequence number"
            )
        value = bytearray(
            [
                ((transaction_id.source_id.byte_len - 1) << 4)
                | (transaction_id.seq_num.byte_len - 1)
            ]
        )
        value.extend(transaction_id.source_id.as_bytes)
        value.extend(transaction_id.seq_num.as_bytes)
        super().__init__(ORIGINATING_TRANSACTION_ID_MSG_TYPE_ID, value)


@dataclasses.dataclass
class DirectoryParams:
    dir_path: CfdpLv
    dir_file_name: CfdpLv

    @classmethod
    def from_strs(cls, dir_path: str, dir_file_name: str) -> DirectoryParams:
        return cls(CfdpLv.from_str(dir_path), CfdpLv.from_str(dir_file_name))

    @classmethod
    def from_paths(cls, dir_path: Path, dir_file_name: Path) -> DirectoryParams:
        return cls(CfdpLv.from_path(dir_path), CfdpLv.from_path(dir_file_name))

    @property
    def dir_path_as_str(self) -> str:
        return self.dir_path.value.decode()

    @property
    def dir_path_as_path(self) -> Path:
        return Path(self.dir_path_as_str)

    @property
    def dir_file_name_as_str(self) -> str:
        return self.dir_file_name.value.decode()

    @property
    def dir_file_name_as_path(self) -> Path:
        return Path(self.dir_file_name_as_str)


@dataclasses.dataclass
class DirListingOptions:
    recursive: bool
    all: bool


class DirectoryListingRequest(ReservedCfdpMessage):
    def __init__(self, params: DirectoryParams):
        """Create a directory listing request."""
        value = params.dir_path.pack() + params.dir_file_name.pack()
        super().__init__(DirectoryOperationMessageType.LISTING_REQUEST, value)


class DirectoryListingResponse(ReservedCfdpMessage):
    def __init__(self, listing_success: bool, dir_params: DirectoryParams):
        """Create a directory listing response.

        Parameters
        -------------

        listing_reponse:
            True if the respondent CFDP user is able to proive a directory listing file.
        dir_params:
            Parameters specified by the corresponding listing request.
        """
        value = (
            bytes([listing_success << 7])
            + dir_params.dir_path.pack()
            + dir_params.dir_file_name.pack()
        )
        super().__init__(DirectoryOperationMessageType.LISTING_RESPONSE, value)


class DirectoryListingParameters(ReservedCfdpMessage):
    def __init__(self, options: DirListingOptions):
        """This is a custom reserved CFDP message to address a shortcoming of the CFDP standard
        for directory listings.The all option could translate to something like the ``-a`` option
        for the ``ls`` command to also display hidden files."""
        super().__init__(
            DirectoryOperationMessageType.CUSTOM_LISTING_PARAMETERS,
            bytes([(options.recursive << 1) | options.all]),
        )


class TlvHolder:
    def __init__(self, tlv: Optional[AbstractTlvBase]):
        self.tlv = tlv

    @property
    def tlv_type(self):
        if self.tlv is not None:
            return self.tlv.tlv_type

    def __cast_internally(
        self,
        obj_type: Type[AbstractTlvBase],
        expected_type: TlvType,
    ) -> Any:
        assert self.tlv is not None
        if self.tlv.tlv_type != expected_type:
            raise TypeError(f"Invalid object {self.tlv} for type {self.tlv.tlv_type}")
        return cast(obj_type, self.tlv)

    def to_fs_request(self) -> FileStoreRequestTlv:
        # Check this type first. It's a concrete type where we can not just use a simple cast
        if isinstance(self.tlv, CfdpTlv):
            return FileStoreRequestTlv.from_tlv(self.tlv)
        return self.__cast_internally(FileStoreRequestTlv, TlvType.FILESTORE_REQUEST)

    def to_fs_response(self) -> FileStoreResponseTlv:
        if isinstance(self.tlv, CfdpTlv):
            return FileStoreResponseTlv.from_tlv(self.tlv)
        return self.__cast_internally(FileStoreResponseTlv, TlvType.FILESTORE_RESPONSE)

    def to_msg_to_user(self) -> MessageToUserTlv:
        if isinstance(self.tlv, CfdpTlv):
            return MessageToUserTlv.from_tlv(self.tlv)
        return self.__cast_internally(MessageToUserTlv, TlvType.MESSAGE_TO_USER)

    def to_fault_handler_override(self) -> FaultHandlerOverrideTlv:
        if isinstance(self.tlv, CfdpTlv):
            return FaultHandlerOverrideTlv.from_tlv(self.tlv)
        return self.__cast_internally(FaultHandlerOverrideTlv, TlvType.FAULT_HANDLER)

    def to_flow_label(self) -> FlowLabelTlv:
        if isinstance(self.tlv, CfdpTlv):
            return FlowLabelTlv.from_tlv(self.tlv)
        return self.__cast_internally(FlowLabelTlv, TlvType.FLOW_LABEL)

    def to_entity_id(self) -> EntityIdTlv:
        if isinstance(self.tlv, CfdpTlv):
            return EntityIdTlv.from_tlv(self.tlv)
        return self.__cast_internally(EntityIdTlv, TlvType.ENTITY_ID)
