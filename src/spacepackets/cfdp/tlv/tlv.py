from __future__ import annotations

from spacepackets.cfdp.defs import (
    ConditionCode,
    FaultHandlerCode,
)
from spacepackets.cfdp.lv import CfdpLv
from spacepackets.cfdp.tlv.base import AbstractTlvBase
from spacepackets.cfdp.tlv.defs import (
    FilestoreActionCode,
    FilestoreResponseStatusCode,
    TlvType,
    TlvTypeMissmatchError,
)
from spacepackets.exceptions import BytesTooShortError
from spacepackets.util import UnsignedByteField


def map_enum_status_code_to_int(status_code: FilestoreResponseStatusCode) -> int:
    return status_code & 0x0F


def map_enum_status_code_to_action_status_code(
    status_code_enum: FilestoreResponseStatusCode,
) -> tuple[FilestoreActionCode, int]:
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
        return FilestoreResponseStatusCode(action_code << 4 | status_code)
    except (IndexError, ValueError):
        return FilestoreResponseStatusCode.INVALID


class CfdpTlv(AbstractTlvBase):
    """Encapsulates the CFDP Type-Length-Value (TLV) format.
    For more information, refer to CCSDS 727.0-B-5 p.77
    """

    MINIMAL_LEN = 2

    def __init__(self, tlv_type: TlvType, value: bytes | bytearray):
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
    def tlv_type(self) -> TlvType:
        return self._tlv_type

    @tlv_type.setter
    def tlv_type(self, tlv_type: TlvType) -> None:
        self._tlv_type = tlv_type

    @property
    def value(self) -> bytes:
        return bytes(self._value)

    def pack(self) -> bytearray:
        tlv_data = bytearray()
        tlv_data.append(self.tlv_type)
        tlv_data.append(self.value_len)
        tlv_data.extend(self._value)
        return tlv_data

    @classmethod
    def unpack(cls, data: bytes | bytearray) -> CfdpTlv:
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
        except ValueError as err:
            raise ValueError(
                f"TLV field invalid, found value {data[0]} is not a possible TLV parameter"
            ) from err

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
        return f"{self.__class__.__name__}(tlv_type={self.tlv_type!r}, value={self.value!r})"

    def __str__(self):
        return (
            f"CFDP TLV with type {self.tlv_type} and data"
            f" 0x[{self._value.hex(sep=',')}] with length {len(self._value)}"
        )


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
    def packet_len(self) -> int:
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
        fault_handler_ovr_tlv.condition_code = (fault_handler_ovr_tlv.tlv.value[0] & 0xF0) >> 4
        fault_handler_ovr_tlv.handler_code = fault_handler_ovr_tlv.tlv.value[0] & 0x0F
        return fault_handler_ovr_tlv

    @classmethod
    def from_tlv(cls, cfdp_tlv: CfdpTlv) -> FaultHandlerOverrideTlv:
        if cfdp_tlv.tlv_type != cls.TLV_TYPE:
            raise TlvTypeMissmatchError(cfdp_tlv.tlv_type, cls.TLV_TYPE)
        fault_handler_tlv = cls.__empty()
        fault_handler_tlv.tlv = cfdp_tlv
        fault_handler_tlv.condition_code = (cfdp_tlv.value[0] >> 4) & 0x0F
        fault_handler_tlv.handler_code = cfdp_tlv.value[0] & 0x0F
        return fault_handler_tlv


def create_cfdp_proxy_and_dir_op_message_marker() -> bytes:
    """CCSDS 727.0-B-5 p.88: The message identifier for standard CFDP proxy and dir op messages
    is the presence of the ASCII characters 'cfdp' in the first four octests of each message
    """
    return b"cfdp"


class FlowLabelTlv(AbstractTlvBase):
    TLV_TYPE = TlvType.FLOW_LABEL

    def __init__(self, flow_label: bytes):
        self.tlv = CfdpTlv(tlv_type=self.tlv_type, value=flow_label)

    @classmethod
    def __empty(cls) -> FlowLabelTlv:
        return cls(b"")

    def pack(self) -> bytearray:
        return self.tlv.pack()

    @property
    def packet_len(self) -> int:
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
            raise TlvTypeMissmatchError(tlv.tlv_type, cls.TLV_TYPE)
        flow_label_tlv.tlv = tlv
        return flow_label_tlv

    @classmethod
    def from_tlv(cls, cfdp_tlv: CfdpTlv) -> FlowLabelTlv:
        if cfdp_tlv.tlv_type != FlowLabelTlv.TLV_TYPE:
            raise TlvTypeMissmatchError(cfdp_tlv.tlv_type, cls.TLV_TYPE)
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
        self.tlv: CfdpTlv | None = None

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
    def _check_raw_tlv_field(first_byte: int, expected: TlvType) -> None:
        try:
            raw_tlv_type = TlvType(first_byte)
            if raw_tlv_type != expected:
                raise TlvTypeMissmatchError(raw_tlv_type, expected)
        except IndexError as err:
            raise ValueError(f"No TLV type for raw field {first_byte}") from err

    @staticmethod
    def _common_unpacker(
        raw_bytes: bytes | bytearray,
    ) -> tuple[FilestoreActionCode, str, int, int, str | None]:
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
        except ValueError as err:
            raise ValueError(
                f"Invalid action code in file store response with value {action_code_as_int}"
            ) from err
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

    def generate_tlv(self) -> None:
        if self.tlv is None:
            self.tlv = self._build_tlv()

    def pack(self) -> bytearray:
        self.generate_tlv()
        return self.tlv.pack()

    @property
    def packet_len(self) -> int:
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
            raise TlvTypeMissmatchError(cfdp_tlv.tlv_type, cls.TLV_TYPE)
        fs_response = cls.__empty()
        cls._set_fields(fs_response, cfdp_tlv.value)
        return fs_response

    @classmethod
    def _set_fields(cls, instance: FileStoreRequestTlv, raw_data: bytes) -> FileStoreRequestTlv:
        action_code, first_name, _, _, second_name = cls._common_unpacker(raw_bytes=raw_data)
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
        filestore_msg: None | CfdpLv = None,
    ):
        if filestore_msg is None:
            filestore_msg = CfdpLv(value=b"")
        super().__init__(
            action_code=action_code,
            first_file_name=first_file_name,
            second_file_name=second_file_name,
        )
        self.status_code = status_code
        self.filestore_msg = filestore_msg

    def generate_tlv(self) -> None:
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
    def packet_len(self) -> int:
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
    def unpack(cls, data: bytes | bytearray) -> FileStoreResponseTlv:
        cls._check_raw_tlv_field(data[0], FileStoreResponseTlv.TLV_TYPE)
        filestore_reply = cls.__empty()
        cls._set_fields(filestore_reply, data[2:])
        return filestore_reply

    @classmethod
    def from_tlv(cls, cfdp_tlv: CfdpTlv) -> FileStoreResponseTlv:
        if cfdp_tlv.tlv_type != cls.TLV_TYPE:
            raise TlvTypeMissmatchError(cfdp_tlv.tlv_type, cls.TLV_TYPE)
        fs_response = FileStoreResponseTlv.__empty()
        cls._set_fields(fs_response, cfdp_tlv.value)
        return fs_response

    @classmethod
    def _set_fields(cls, instance: FileStoreResponseTlv, data: bytes | bytearray) -> None:
        action_code, first_name, status_code, idx, second_name = cls._common_unpacker(
            raw_bytes=data
        )
        instance.action_code = action_code
        instance.first_file_name = first_name
        try:
            status_code_named = FilestoreResponseStatusCode(action_code << 4 | status_code)
        except ValueError as err:
            raise ValueError(
                "Invalid status code in file store response with value"
                f" {status_code} for action code {action_code}"
            ) from err
        instance.status_code = status_code_named
        if second_name is not None:
            instance.second_file_name = second_name
        instance.filestore_msg = CfdpLv.unpack(data[idx:])


class EntityIdTlv(AbstractTlvBase):
    """This helper class has a :py:meth:`__eq__` implementation which only compares the numerical
    value of the entity IDs"""

    TLV_TYPE = TlvType.ENTITY_ID

    def __init__(self, entity_id: bytes):
        self.tlv = CfdpTlv(tlv_type=TlvType.ENTITY_ID, value=entity_id)

    def pack(self) -> bytearray:
        return self.tlv.pack()

    @property
    def packet_len(self) -> int:
        return self.tlv.packet_len

    @property
    def tlv_type(self) -> TlvType:
        return EntityIdTlv.TLV_TYPE

    @property
    def value(self) -> bytes:
        return self.tlv.value

    @classmethod
    def __empty(cls) -> EntityIdTlv:
        return cls(entity_id=b"")

    @classmethod
    def unpack(cls, data: bytes | bytearray) -> EntityIdTlv:
        entity_id_tlv = cls.__empty()
        entity_id_tlv.tlv = CfdpTlv.unpack(data=data)
        entity_id_tlv.check_type(tlv_type=TlvType.ENTITY_ID)
        return entity_id_tlv

    @classmethod
    def from_tlv(cls, cfdp_tlv: CfdpTlv) -> EntityIdTlv:
        if cfdp_tlv.tlv_type != cls.TLV_TYPE:
            raise TlvTypeMissmatchError(cfdp_tlv.tlv_type, cls.TLV_TYPE)
        entity_id_tlv = cls.__empty()
        entity_id_tlv.tlv = cfdp_tlv
        return entity_id_tlv

    def __eq__(self, other: AbstractTlvBase) -> bool:
        """Custom implementation which only compares the numerical value of the entity IDs"""
        if not isinstance(other, EntityIdTlv):
            return False
        own_id = UnsignedByteField.from_bytes(self.value)
        other_id = UnsignedByteField.from_bytes(other.value)
        return own_id.value == other_id.value

    def __hash__(self) -> int:
        return super().__hash__()
