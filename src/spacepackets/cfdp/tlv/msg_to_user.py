"""This submodule contains the Message To User TLV abstractions. It also contains
the Reserved CFDP Message abstractions which are a subtype of the Message To User TLV.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import TYPE_CHECKING

from spacepackets.cfdp.defs import (
    ConditionCode,
    DeliveryCode,
    FileStatus,
    TransactionId,
    TransmissionMode,
)
from spacepackets.cfdp.lv import CfdpLv
from spacepackets.cfdp.tlv.base import AbstractTlvBase
from spacepackets.cfdp.tlv.defs import (
    ORIGINATING_TRANSACTION_ID_MSG_TYPE_ID,
    DirectoryOperationMessageType,
    ProxyMessageType,
    TlvType,
    TlvTypeMissmatchError,
)
from spacepackets.cfdp.tlv.tlv import CfdpTlv
from spacepackets.util import UnsignedByteField

if TYPE_CHECKING:
    from spacepackets.cfdp.pdu.finished import FinishedParams


class MessageToUserTlv(AbstractTlvBase):
    """Message to User TLV implementation as specified in CCSDS 727.0-B-5 5.4.3"""

    TLV_TYPE = TlvType.MESSAGE_TO_USER

    def __init__(self, msg: bytes):
        self.tlv = CfdpTlv(tlv_type=MessageToUserTlv.TLV_TYPE, value=msg)

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
        return MessageToUserTlv.TLV_TYPE

    def is_reserved_cfdp_message(self) -> bool:
        return bool(len(self.tlv.value) >= 5 and self.tlv.value[0:4].decode() == "cfdp")

    def to_reserved_msg_tlv(self) -> ReservedCfdpMessage | None:
        """Attempt to convert to a reserved CFDP message. Please note that this operation
        will fail if the message if not a reserved CFDP message and will then return None.
        This method is especially useful to have access to the more specialized
        :py:class:`ReservedCfdpMessage` API."""
        if not self.is_reserved_cfdp_message():
            return None
        return ReservedCfdpMessage(self.tlv.value[4], self.tlv.value[5:])

    @classmethod
    def __empty(cls) -> MessageToUserTlv:
        return cls(b"")

    @classmethod
    def unpack(cls, data: bytes | bytearray) -> MessageToUserTlv:
        msg_to_user_tlv = cls.__empty()
        msg_to_user_tlv.tlv = CfdpTlv.unpack(data)
        msg_to_user_tlv.check_type(MessageToUserTlv.TLV_TYPE)
        return msg_to_user_tlv

    @classmethod
    def from_tlv(cls, cfdp_tlv: CfdpTlv) -> MessageToUserTlv:
        if cfdp_tlv.tlv_type != cls.TLV_TYPE:
            raise TlvTypeMissmatchError(cfdp_tlv.tlv_type, cls.TLV_TYPE)
        msg_to_user_tlv = cls.__empty()
        msg_to_user_tlv.tlv = cfdp_tlv
        return msg_to_user_tlv


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

    def __init__(self, msg_type: int, value: bytes | bytearray):
        assert msg_type < pow(2, 8) - 1
        full_value = bytearray(b"cfdp")
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
    def packet_len(self) -> int:
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
        return self.get_reserved_cfdp_message_type() == ORIGINATING_TRANSACTION_ID_MSG_TYPE_ID

    def get_cfdp_proxy_message_type(self) -> ProxyMessageType | None:
        if not self.is_cfdp_proxy_operation():
            return None
        return ProxyMessageType(self.get_reserved_cfdp_message_type())

    def get_directory_operation_type(self) -> DirectoryOperationMessageType | None:
        if not self.is_directory_operation():
            return None
        return DirectoryOperationMessageType(self.get_reserved_cfdp_message_type())

    def get_originating_transaction_id(
        self,
    ) -> TransactionId | None:
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

    def get_proxy_put_request_params(self) -> ProxyPutRequestParams | None:
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
        return ProxyPutRequestParams(
            UnsignedByteField.from_bytes(dest_id_lv.value),
            source_name_lv,
            dest_name_lv,
        )

    def get_proxy_put_response_params(self) -> ProxyPutResponseParams | None:
        if (
            not self.is_cfdp_proxy_operation()
            or self.get_cfdp_proxy_message_type() != ProxyMessageType.PUT_RESPONSE
        ):
            return None
        condition_code = ConditionCode((self.value[5] >> 4) & 0b1111)
        delivery_code = DeliveryCode((self.value[5] >> 2) & 0b1)
        file_status = FileStatus(self.value[5] & 0b11)
        return ProxyPutResponseParams(condition_code, delivery_code, file_status)

    def get_proxy_closure_requested(self) -> bool | None:
        if (
            not self.is_cfdp_proxy_operation()
            or self.get_cfdp_proxy_message_type() != ProxyMessageType.CLOSURE_REQUEST
        ):
            return None
        return bool(self.value[5] & 0b1)

    def get_proxy_transmission_mode(self) -> TransmissionMode | None:
        if (
            not self.is_cfdp_proxy_operation()
            or self.get_cfdp_proxy_message_type() != ProxyMessageType.TRANSMISSION_MODE
        ):
            return None
        return TransmissionMode(self.value[5] & 0b1)

    def get_dir_listing_request_params(self) -> DirectoryParams | None:
        if (
            not self.is_directory_operation()
            or self.get_directory_operation_type() != DirectoryOperationMessageType.LISTING_REQUEST
        ):
            return None
        dir_path_lv = CfdpLv.unpack(self.value[5:])
        dir_file_name_lv = CfdpLv.unpack(self.value[5 + dir_path_lv.packet_len :])
        return DirectoryParams(dir_path_lv, dir_file_name_lv)

    def get_dir_listing_response_params(self) -> tuple[bool, DirectoryParams] | None:
        """
        Returns
        ---------
            None if this is not a directory listing response. Otherwise, returns a tuple where
            the first entry is a boolean denoting whether the directory listing response was
            generated succesfully, and the second entry being the directory listing parameters.
        """
        if (
            not self.is_directory_operation()
            or self.get_directory_operation_type() != DirectoryOperationMessageType.LISTING_RESPONSE
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

    def get_dir_listing_options(self) -> DirListingOptions | None:
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
        return DirListingOptions(bool((self.value[5] >> 1) & 0b1), bool(self.value[5] & 0b1))


@dataclasses.dataclass
class ProxyPutRequestParams:
    dest_entity_id: UnsignedByteField
    source_file_name: CfdpLv
    dest_file_name: CfdpLv

    @property
    def source_file_as_str(self) -> str:
        return self.source_file_name.value.decode()

    @property
    def source_file_as_path(self) -> Path:
        return Path(self.source_file_as_str)

    @property
    def dest_file_as_str(self) -> str:
        return self.dest_file_name.value.decode()

    @property
    def dest_file_as_path(self) -> Path:
        return Path(self.dest_file_as_str)


class ProxyPutRequest(ReservedCfdpMessage):
    def __init__(self, params: ProxyPutRequestParams):
        value = CfdpLv(params.dest_entity_id.as_bytes).pack()
        value.extend(params.source_file_name.pack())
        value.extend(params.dest_file_name.pack())
        super().__init__(ProxyMessageType.PUT_REQUEST, value)


class ProxyCancelRequest(ReservedCfdpMessage):
    def __init__(self):
        super().__init__(ProxyMessageType.PUT_CANCEL, b"")


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
            [((transaction_id.source_id.byte_len - 1) << 4) | (transaction_id.seq_num.byte_len - 1)]
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


@dataclasses.dataclass
class ProxyPutResponseParams:
    condition_code: ConditionCode
    delivery_code: DeliveryCode
    file_status: FileStatus

    @classmethod
    def from_finished_params(cls, finished_params: FinishedParams) -> ProxyPutResponseParams:
        return cls(
            condition_code=finished_params.condition_code,
            delivery_code=finished_params.delivery_code,
            file_status=finished_params.file_status,
        )


class ProxyPutResponse(ReservedCfdpMessage):
    def __init__(self, params: ProxyPutResponseParams):
        super().__init__(
            ProxyMessageType.PUT_RESPONSE,
            bytes(
                [(params.condition_code << 4) | (params.delivery_code << 2) | params.file_status]
            ),
        )
