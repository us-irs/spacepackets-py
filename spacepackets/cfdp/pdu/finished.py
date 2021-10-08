from __future__ import annotations
import enum

from spacepackets.cfdp.pdu.file_directive import FileDirectivePduBase, DirectiveCodes, ConditionCode
from spacepackets.cfdp.conf import check_packet_length, PduConfig
from spacepackets.cfdp.tlv import CfdpTlv
from spacepackets.log import get_console_logger
from typing import List


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
    MINIMAL_LEN = FileDirectivePduBase.FILE_DIRECTIVE_PDU_LEN + 1

    def __init__(
            self,
            delivery_code: DeliveryCode,
            file_delivery_status: FileDeliveryStatus,
            pdu_conf: PduConfig,
            condition_code: ConditionCode = ConditionCode.NO_ERROR,
            file_store_responses: List[CfdpTlv] = None,
            fault_location: CfdpTlv = None,

    ):
        self.pdu_file_directive = FileDirectivePduBase(
            directive_code=DirectiveCodes.FINISHED_PDU,
            pdu_conf=pdu_conf,
            directive_param_field_len=0
        )
        self.condition_code = condition_code
        self.delivery_code = delivery_code
        if file_store_responses is None:
            self.file_store_responses = []
        else:
            self.file_store_responses = file_store_responses
        self.fault_location = fault_location
        self.file_delivery_status = file_delivery_status
        self.might_have_fault_location = False
        if self.condition_code != ConditionCode.NO_ERROR and \
                self.condition_code != ConditionCode.UNSUPPORTED_CHECKSUM_TYPE:
            self.might_have_fault_location = True

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
        packet[len(packet)] |= \
            (self.condition_code << 4) | (self.delivery_code << 2) | self.file_delivery_status
        for file_store_reponse in self.file_store_responses:
            packet.extend(file_store_reponse.pack())
        if self.fault_location is not None:
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
        if not check_packet_length(raw_packet_len=len(raw_packet), min_len=cls.MINIMAL_LEN):
            raise ValueError
        current_idx = finished_pdu.pdu_file_directive.get_packet_len()
        first_param_byte = raw_packet[current_idx]
        finished_pdu.condition_code = first_param_byte & 0xf0
        finished_pdu.delivery_code = first_param_byte & 0x04
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
            current_idx += current_tlv.get_total_length()
            if current_idx > len(raw_packet) or current_idx == len(raw_packet):
                if current_idx > len(raw_packet):
                    logger = get_console_logger()
                    logger.warning(
                        'Parser Error when parsing TLVs in Finished PDU. Possibly invalid packet'
                    )
                if self.might_have_fault_location:
                    self.fault_location = current_tlv
                else:
                    self.file_store_responses.append(current_tlv)
                break
            else:
                # Another TLV might follow, so this is a file store response
                self.file_store_responses.append(current_tlv)
        return current_idx
