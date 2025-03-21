from __future__ import annotations  # Python 3.9 compatibility for | syntax

from typing import Any

from spacepackets.cfdp.tlv.defs import TlvType
from spacepackets.cfdp.tlv.msg_to_user import MessageToUserTlv
from spacepackets.cfdp.tlv.tlv import (
    AbstractTlvBase,
    CfdpTlv,
    EntityIdTlv,
    FaultHandlerOverrideTlv,
    FileStoreRequestTlv,
    FileStoreResponseTlv,
    FlowLabelTlv,
)


class TlvHolder:
    def __init__(self, tlv: AbstractTlvBase | None):
        self.tlv = tlv

    @property
    def tlv_type(self) -> None | TlvType:
        if self.tlv is not None:
            return self.tlv.tlv_type
        return None

    def __cast_internally(
        self,
        obj_type: type[AbstractTlvBase],
        expected_type: TlvType,
    ) -> Any:  # noqa: ANN401
        assert self.tlv is not None
        if self.tlv.tlv_type != expected_type or not isinstance(self.tlv, obj_type):
            raise TypeError(f"Invalid object {self.tlv} for type {self.tlv.tlv_type}")
        return self.tlv

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
