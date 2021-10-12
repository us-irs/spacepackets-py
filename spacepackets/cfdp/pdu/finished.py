from __future__ import annotations
import enum
from typing import List, Optional

from spacepackets.cfdp.pdu.file_directive import FileDirectivePduBase, DirectiveCodes, ConditionCode
from spacepackets.cfdp.conf import check_packet_length, PduConfig
from spacepackets.cfdp.tlv import CfdpTlv, TlvTypes
from spacepackets.log import get_console_logger


class DeliveryCode(enum.IntEnum):
    DATA_COMPLETE = 0
    DATA_INCOMPLETE = 1


class FileDeliveryStatus(enum.IntEnum):
    DISCARDED_DELIBERATELY = 0
    DISCARDED_FILESTORE_REJECTION = 1
    FILE_RETAINED = 2
    FILE_STATUS_UNREPORTED = 3


class FinishedPdu:
    """Encapsulates the Finished file directive PDU, see CCSDS 727.0-B-5 p.80"""

    def __init__(
            self,
            delivery_code: DeliveryCode,
            file_delivery_status: FileDeliveryStatus,
            condition_code: ConditionCode,
            pdu_conf: PduConfig,
            file_store_responses: Optional[List[CfdpTlv]] = None,
            fault_location: Optional[CfdpTlv] = None,

    ):
        self.pdu_file_directive = FileDirectivePduBase(
            directive_code=DirectiveCodes.FINISHED_PDU,
            pdu_conf=pdu_conf,
            directive_param_field_len=1
        )
        self._fault_location = None
        self._file_store_responses = []
        self._might_have_fault_location = False
        self.condition_code = condition_code
        self.delivery_code = delivery_code
        self.fault_location = fault_location
        self.file_store_responses = file_store_responses
        self.file_delivery_status = file_delivery_status

    @property
    def condition_code(self) -> ConditionCode:
        return self._condition_code

    @condition_code.setter
    def condition_code(self, condition_code: ConditionCode):
        if condition_code in [ConditionCode.NO_ERROR, ConditionCode.UNSUPPORTED_CHECKSUM_TYPE]:
            self._might_have_fault_location = False
        else:
            self._might_have_fault_location = True
        self._condition_code = condition_code

    @property
    def packet_len(self) -> int:
        return self.pdu_file_directive.packet_len

    @property
    def file_store_responses(self) -> List[CfdpTlv]:
        return self._file_store_responses

    @file_store_responses.setter
    def file_store_responses(self, file_store_responses: Optional[List[CfdpTlv]]):
        """Setter function for the file store responses
        :param file_store_responses:
        :raises ValueError: TLV type is not a filestore response
        :return:
        """
        if file_store_responses is None:
            self._file_store_responses = []
            self.pdu_file_directive.directive_param_field_len = 1 + self.fault_location_len
            return
        else:
            for file_store_response in file_store_responses:
                if file_store_response.tlv_type != TlvTypes.FILESTORE_RESPONSE:
                    raise ValueError
        self._file_store_responses = file_store_responses
        self.pdu_file_directive.directive_param_field_len = \
            1 + self.fault_location_len + self.file_store_responses_len

    @property
    def file_store_responses_len(self):
        if not self._file_store_responses:
            return 0
        else:
            file_store_responses_len = 0
            for file_store_response in self._file_store_responses:
                file_store_responses_len += file_store_response.packet_length
            return file_store_responses_len

    @property
    def fault_location(self):
        return self._fault_location

    @fault_location.setter
    def fault_location(self, fault_location: Optional[CfdpTlv]):
        """Setter function for the fault location.
        :raises ValueError: Type ID is not entity ID (0x06)
        """
        if fault_location is None:
            fault_loc_len = 0
        else:
            if fault_location.tlv_type != TlvTypes.ENTITY_ID:
                raise ValueError
            fault_loc_len = self.fault_location_len
        self.pdu_file_directive.directive_param_field_len = \
            1 + fault_loc_len + self.file_store_responses_len
        self._fault_location = fault_location

    @property
    def fault_location_len(self):
        if self._fault_location is None:
            return 0
        else:
            return self._fault_location.packet_length

    @classmethod
    def __empty(cls) -> FinishedPdu:
        empty_conf = PduConfig.empty()
        return cls(
            delivery_code=DeliveryCode.DATA_INCOMPLETE,
            file_delivery_status=FileDeliveryStatus.FILE_STATUS_UNREPORTED,
            condition_code=ConditionCode.NO_ERROR,
            pdu_conf=empty_conf
        )

    def pack(self) -> bytearray:
        packet = self.pdu_file_directive.pack()
        packet.append(
            (self.condition_code << 4) | (self.delivery_code << 2) | self.file_delivery_status
        )
        for file_store_reponse in self.file_store_responses:
            packet.extend(file_store_reponse.pack())
        if self.fault_location is not None and self._might_have_fault_location:
            packet.extend(self.fault_location.pack())
        return packet

    @classmethod
    def unpack(cls, raw_packet: bytearray) -> FinishedPdu:
        """Unpack a raw packet into a PDU object
        :param raw_packet:
        :raise ValueError: If packet is too short
        :return:
        """
        finished_pdu = cls.__empty()
        finished_pdu.pdu_file_directive = FileDirectivePduBase.unpack(raw_packet=raw_packet)
        if not check_packet_length(
                raw_packet_len=len(raw_packet), min_len=finished_pdu.pdu_file_directive.packet_len
        ):
            raise ValueError
        current_idx = finished_pdu.pdu_file_directive.header_len
        first_param_byte = raw_packet[current_idx]
        finished_pdu.condition_code = (first_param_byte & 0xf0) >> 4
        finished_pdu.delivery_code = (first_param_byte & 0x04) >> 2
        finished_pdu.file_delivery_status = first_param_byte & 0b11
        current_idx += 1
        if len(raw_packet) > current_idx:
            finished_pdu.unpack_tlvs(raw_packet=raw_packet, start_idx=current_idx)
        return finished_pdu

    def unpack_tlvs(self, raw_packet: bytearray, start_idx: int) -> int:
        current_idx = start_idx
        while True:
            current_tlv = CfdpTlv.unpack(raw_bytes=raw_packet[current_idx:])
            # This will always increment at least two, so we can't get stuck in the loop
            current_idx += current_tlv.packet_length
            if current_idx >= len(raw_packet):
                if current_idx > len(raw_packet):
                    logger = get_console_logger()
                    logger.warning(
                        'Parser Error when parsing TLVs in Finished PDU. Possibly invalid packet'
                    )
                if self._might_have_fault_location:
                    self.fault_location = current_tlv
                else:
                    self.file_store_responses.append(current_tlv)
                break
            else:
                # Another TLV might follow, so this is a file store response
                self.file_store_responses.append(current_tlv)
        return current_idx
