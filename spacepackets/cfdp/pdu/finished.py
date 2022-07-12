from __future__ import annotations
import enum
from dataclasses import dataclass
from typing import List, Optional, cast

from spacepackets.cfdp.pdu import PduHeader
from spacepackets.cfdp.pdu.file_directive import (
    FileDirectivePduBase,
    DirectiveType,
    AbstractFileDirectiveBase,
)
from spacepackets.cfdp.defs import ConditionCode
from spacepackets.cfdp.conf import check_packet_length, PduConfig
from spacepackets.cfdp.tlv import TlvTypes, FileStoreResponseTlv, EntityIdTlv
from spacepackets.log import get_console_logger


class DeliveryCode(enum.IntEnum):
    DATA_COMPLETE = 0
    DATA_INCOMPLETE = 1


class FileDeliveryStatus(enum.IntEnum):
    DISCARDED_DELIBERATELY = 0
    DISCARDED_FILESTORE_REJECTION = 1
    FILE_RETAINED = 2
    FILE_STATUS_UNREPORTED = 3


@dataclass
class FinishedParams:
    delivery_code: DeliveryCode
    delivery_status: FileDeliveryStatus
    condition_code: ConditionCode
    file_store_responses: Optional[List[FileStoreResponseTlv]] = None
    fault_location: Optional[EntityIdTlv] = None

    @classmethod
    def empty(cls) -> FinishedParams:
        return cls(
            delivery_code=DeliveryCode.DATA_COMPLETE,
            delivery_status=FileDeliveryStatus.DISCARDED_DELIBERATELY,
            condition_code=ConditionCode.NO_ERROR,
        )


class FinishedPdu(AbstractFileDirectiveBase):
    """Encapsulates the Finished file directive PDU, see CCSDS 727.0-B-5 p.80"""

    def __init__(
        self,
        params: FinishedParams,
        pdu_conf: PduConfig,
    ):
        self.pdu_file_directive = FileDirectivePduBase(
            directive_code=DirectiveType.FINISHED_PDU,
            pdu_conf=pdu_conf,
            directive_param_field_len=1,
        )
        self._fault_location = None
        self._file_store_responses = []
        self._might_have_fault_location = False
        self._params = params

    @property
    def directive_type(self) -> DirectiveType:
        return DirectiveType.FINISHED_PDU

    @property
    def pdu_header(self) -> PduHeader:
        return self.pdu_file_directive.pdu_header

    @property
    def condition_code(self) -> ConditionCode:
        return self._params.condition_code

    @condition_code.setter
    def condition_code(self, condition_code: ConditionCode):
        if condition_code in [
            ConditionCode.NO_ERROR,
            ConditionCode.UNSUPPORTED_CHECKSUM_TYPE,
        ]:
            self._might_have_fault_location = False
        else:
            self._might_have_fault_location = True
        self._params.condition_code = condition_code

    @property
    def packet_len(self) -> int:
        return self.pdu_file_directive.packet_len

    @property
    def file_store_responses(self) -> List[FileStoreResponseTlv]:
        return self._params.file_store_responses

    @file_store_responses.setter
    def file_store_responses(
        self, file_store_responses: Optional[List[FileStoreResponseTlv]]
    ):
        """Setter function for the file store responses
        :param file_store_responses:
        :raises ValueError: TLV type is not a filestore response
        :return:
        """
        if file_store_responses is None:
            self._params.file_store_responses = []
            self.pdu_file_directive.directive_param_field_len = (
                1 + self.fault_location_len
            )
            return
        self._params.file_store_responses = file_store_responses
        self.pdu_file_directive.directive_param_field_len = (
            1 + self.fault_location_len + self.file_store_responses_len
        )

    @property
    def file_store_responses_len(self):
        if not self._params.file_store_responses:
            return 0
        else:
            file_store_responses_len = 0
            for file_store_response in self._params.file_store_responses:
                file_store_responses_len += file_store_response.packet_len
            return file_store_responses_len

    @property
    def fault_location(self) -> Optional[EntityIdTlv]:
        return self._params.fault_location

    @fault_location.setter
    def fault_location(self, fault_location: Optional[EntityIdTlv]):
        """Setter function for the fault location.
        :raises ValueError: Type ID is not entity ID (0x06)
        """
        if fault_location is None:
            fault_loc_len = 0
        else:
            fault_loc_len = self.fault_location_len
        self.pdu_file_directive.directive_param_field_len = (
            1 + fault_loc_len + self.file_store_responses_len
        )
        self._params.fault_location = fault_location

    @property
    def fault_location_len(self):
        if self._params.fault_location is None:
            return 0
        else:
            return self._params.fault_location.packet_len

    @classmethod
    def __empty(cls) -> FinishedPdu:
        empty_conf = PduConfig.empty()
        return cls(
            params=FinishedParams.empty(),
            pdu_conf=empty_conf,
        )

    def pack(self) -> bytearray:
        packet = self.pdu_file_directive.pack()
        packet.append(
            (self._params.condition_code << 4)
            | (self._params.delivery_code << 2)
            | self._params.delivery_status
        )
        for file_store_reponse in self.file_store_responses:
            packet.extend(file_store_reponse.pack())
        if self.fault_location is not None and self._might_have_fault_location:
            packet.extend(self.fault_location.pack())
        return packet

    @classmethod
    def unpack(cls, raw_packet: bytearray) -> FinishedPdu:
        """Unpack a raw packet into a PDU object.

        :param raw_packet:
        :raise ValueError: If packet is too short
        :return:
        """
        finished_pdu = cls.__empty()
        finished_pdu.pdu_file_directive = FileDirectivePduBase.unpack(
            raw_packet=raw_packet
        )
        if not check_packet_length(
            raw_packet_len=len(raw_packet),
            min_len=finished_pdu.pdu_file_directive.packet_len,
        ):
            raise ValueError
        current_idx = finished_pdu.pdu_file_directive.header_len
        first_param_byte = raw_packet[current_idx]
        finished_pdu._params.condition_code = (first_param_byte & 0xF0) >> 4
        finished_pdu._params.delivery_code = (first_param_byte & 0x04) >> 2
        finished_pdu._params.file_delivery_status = first_param_byte & 0b11
        current_idx += 1
        if len(raw_packet) > current_idx:
            finished_pdu._unpack_tlvs(
                rest_of_packet=raw_packet[current_idx : finished_pdu.packet_len]
            )
        return finished_pdu

    def _unpack_tlvs(self, rest_of_packet: bytearray) -> int:
        current_idx = 0
        while True:
            next_tlv_code = rest_of_packet[current_idx]
            if next_tlv_code == TlvTypes.FILESTORE_RESPONSE:
                next_fs_response = FileStoreResponseTlv.unpack(
                    raw_bytes=rest_of_packet[current_idx:]
                )
                current_idx += next_fs_response.packet_len
                self._file_store_responses.append(next_fs_response)
            elif next_tlv_code == TlvTypes.ENTITY_ID:
                if not self._might_have_fault_location:
                    logger = get_console_logger()
                    logger.warning(
                        "Entity ID found in Finished PDU but wrong condition code"
                    )
                    raise ValueError
                self._fault_location = EntityIdTlv.unpack(
                    raw_bytes=rest_of_packet[current_idx:]
                )
                current_idx += self._fault_location.packet_len
                return current_idx
            else:
                logger = get_console_logger()
                logger.warning("Invalid TLV ID in Finished PDU detected")
                raise ValueError
            if current_idx >= len(rest_of_packet):
                break

    def __eq__(self, other: FinishedPdu):
        pass

    def __repr__(self):
        pass
