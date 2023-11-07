from __future__ import annotations
from typing import Optional, List
from dataclasses import dataclass, field
from spacepackets.cfdp.defs import DeliveryCode, FileStatus, ConditionCode
from spacepackets.cfdp.tlv import FileStoreResponseTlv
from spacepackets.cfdp.tlv.entity_id_tlv import EntityIdTlv


@dataclass
class FinishedParams:
    delivery_code: DeliveryCode
    file_status: FileStatus
    condition_code: ConditionCode
    file_store_responses: List[FileStoreResponseTlv] = field(default_factory=lambda: [])
    fault_location: Optional[EntityIdTlv] = None

    @classmethod
    def empty(cls) -> FinishedParams:
        return cls(
            delivery_code=DeliveryCode.DATA_COMPLETE,
            file_status=FileStatus.DISCARDED_DELIBERATELY,
            condition_code=ConditionCode.NO_ERROR,
        )

    @classmethod
    def success_params(cls) -> FinishedParams:
        """Generate the finished parameters to generate a full success :py:class:`FinishedPdu`
        PDU."""
        return cls(
            delivery_code=DeliveryCode.DATA_COMPLETE,
            file_status=FileStatus.FILE_RETAINED,
            condition_code=ConditionCode.NO_ERROR,
        )
