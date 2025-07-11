from __future__ import annotations

import copy
import struct
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import fastcrc

from spacepackets.cfdp.conf import PduConfig
from spacepackets.cfdp.defs import (
    ConditionCode,
    CrcFlag,
    DeliveryCode,
    Direction,
    FileStatus,
)
from spacepackets.cfdp.pdu.file_directive import (
    AbstractFileDirectiveBase,
    DirectiveType,
    FileDirectivePduBase,
)
from spacepackets.cfdp.tlv.defs import TlvType
from spacepackets.cfdp.tlv.tlv import EntityIdTlv, FileStoreResponseTlv
from spacepackets.exceptions import BytesTooShortError

if TYPE_CHECKING:
    from spacepackets.cfdp.pdu.header import PduHeader


@dataclass
class FinishedParams:
    condition_code: ConditionCode
    delivery_code: DeliveryCode
    file_status: FileStatus
    file_store_responses: list[FileStoreResponseTlv] = field(default_factory=list)
    fault_location: EntityIdTlv | None = None

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


class FinishedPdu(AbstractFileDirectiveBase):
    """Encapsulates the Finished file directive PDU, see CCSDS 727.0-B-5 p.80.

    >>> finished_pdu = FinishedPdu.success_pdu(PduConfig.default())
    >>> finished_pdu.condition_code
    <ConditionCode.NO_ERROR: 0>
    >>> finished_pdu.delivery_code
    <DeliveryCode.DATA_COMPLETE: 0>
    >>> finished_pdu.file_status
    <FileStatus.FILE_RETAINED: 2>
    """

    def __init__(
        self,
        pdu_conf: PduConfig,
        params: FinishedParams,
    ):
        pdu_conf = copy.copy(pdu_conf)
        pdu_conf.direction = Direction.TOWARDS_SENDER
        self.pdu_file_directive = FileDirectivePduBase(
            directive_code=DirectiveType.FINISHED_PDU,
            pdu_conf=pdu_conf,
            directive_param_field_len=1,
        )
        self._params = params
        if params.fault_location is not None:
            self.fault_location = self._params.fault_location
        if params.file_store_responses is not None:
            self.file_store_responses = self._params.file_store_responses

    @classmethod
    def success_pdu(cls, pdu_conf: PduConfig) -> FinishedPdu:
        return cls(pdu_conf=pdu_conf, params=FinishedParams.success_params())

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
    def condition_code(self, condition_code: ConditionCode) -> None:
        self._params.condition_code = condition_code

    @property
    def delivery_code(self) -> DeliveryCode:
        return self._params.delivery_code

    @property
    def file_status(self) -> FileStatus:
        return self._params.file_status

    @property
    def packet_len(self) -> int:
        return self.pdu_file_directive.packet_len

    @property
    def file_store_responses(self) -> list[FileStoreResponseTlv]:
        return self._params.file_store_responses

    @property
    def finished_params(self) -> FinishedParams:
        return self._params

    @property
    def might_have_fault_location(self) -> bool:
        return self._params.condition_code not in [
            ConditionCode.NO_ERROR,
            ConditionCode.UNSUPPORTED_CHECKSUM_TYPE,
        ]

    @file_store_responses.setter
    def file_store_responses(self, file_store_responses: list[FileStoreResponseTlv] | None) -> None:
        """Setter function for the file store responses
        :param file_store_responses:
        :raises ValueError: TLV type is not a filestore response
        :return:
        """
        if file_store_responses is None:
            self._params.file_store_responses = []
        else:
            self._params.file_store_responses = file_store_responses
        self._calculate_directive_field_len()

    @property
    def file_store_responses_len(self) -> int:
        if not self._params.file_store_responses:
            return 0
        file_store_responses_len = 0
        for file_store_response in self._params.file_store_responses:
            file_store_responses_len += file_store_response.packet_len
        return file_store_responses_len

    @property
    def fault_location(self) -> EntityIdTlv | None:
        return self._params.fault_location

    @fault_location.setter
    def fault_location(self, fault_location: EntityIdTlv | None) -> None:
        """Setter function for the fault location.
        :raises ValueError: Type ID is not entity ID (0x06)
        """
        self._params.fault_location = fault_location
        self._calculate_directive_field_len()

    def _calculate_directive_field_len(self) -> None:
        base_len = 1
        fault_loc_len = 0 if self.fault_location is None else self.fault_location_len
        if self.pdu_file_directive.pdu_conf.crc_flag == CrcFlag.WITH_CRC:
            base_len += 2
        self.pdu_file_directive.directive_param_field_len = (
            base_len + fault_loc_len + self.file_store_responses_len
        )

    @property
    def fault_location_len(self) -> int:
        if self._params.fault_location is None:
            return 0
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
            | self._params.file_status
        )
        if self.file_store_responses is not None:
            for file_store_reponse in self.file_store_responses:
                packet.extend(file_store_reponse.pack())
        if self.fault_location is not None and self.might_have_fault_location:
            packet.extend(self.fault_location.pack())
        if self.pdu_file_directive.pdu_conf.crc_flag == CrcFlag.WITH_CRC:
            packet.extend(struct.pack("!H", fastcrc.crc16.ibm_3740(bytes(packet))))
        return packet

    @classmethod
    def unpack(cls, data: bytes | bytearray) -> FinishedPdu:
        """Generate an object instance from raw data. Care should be taken to check whether
        the raw bytestream really contains a Finished PDU.

        Raises
        --------

        BytesTooShortError
            Raw data too short for expected object.
        ValueError
            Invalid directive type or data format.
        InvalidCrcError
            PDU has a 16 bit CRC and the CRC check failed.
        """
        finished_pdu = cls.__empty()
        finished_pdu.pdu_file_directive = FileDirectivePduBase.unpack(raw_packet=data)
        finished_pdu.pdu_file_directive.verify_length_and_checksum(data)
        if finished_pdu.pdu_file_directive.packet_len > len(data):
            raise BytesTooShortError(finished_pdu.pdu_file_directive.packet_len, len(data))
        current_idx = finished_pdu.pdu_file_directive.header_len
        first_param_byte = data[current_idx]
        params = FinishedParams(
            condition_code=ConditionCode((first_param_byte & 0xF0) >> 4),
            delivery_code=DeliveryCode((first_param_byte & 0x04) >> 2),
            file_status=FileStatus(first_param_byte & 0b11),
        )
        finished_pdu.condition_code = params.condition_code
        finished_pdu._params = params
        current_idx += 1
        end_of_optional_tlvs_idx = finished_pdu.packet_len
        if finished_pdu.pdu_header.crc_flag == CrcFlag.WITH_CRC:
            end_of_optional_tlvs_idx -= 2
        if end_of_optional_tlvs_idx > current_idx:
            finished_pdu._unpack_tlvs(rest_of_packet=data[current_idx:end_of_optional_tlvs_idx])
        return finished_pdu

    def _unpack_tlvs(self, rest_of_packet: bytes | bytearray) -> int:
        current_idx = 0
        fs_responses_list = []
        fault_loc = None
        while True:
            next_tlv_code = rest_of_packet[current_idx]
            if next_tlv_code == TlvType.FILESTORE_RESPONSE:
                next_fs_response = FileStoreResponseTlv.unpack(data=rest_of_packet[current_idx:])
                current_idx += next_fs_response.packet_len
                fs_responses_list.append(next_fs_response)
            elif next_tlv_code == TlvType.ENTITY_ID:
                if not self.might_have_fault_location:
                    raise ValueError("Entity ID found in Finished PDU but wrong condition code")
                fault_loc = EntityIdTlv.unpack(data=rest_of_packet[current_idx:])
                current_idx += fault_loc.packet_len
            else:
                raise ValueError("Invalid TLV ID in Finished PDU detected")
            if current_idx >= len(rest_of_packet):
                break
        if fs_responses_list is not None:
            self.file_store_responses = fs_responses_list
        if fault_loc is not None:
            self.fault_location = fault_loc
        return current_idx

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FinishedPdu):
            return False
        return self._params == other._params and self.pdu_file_directive == other.pdu_file_directive

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(params={self._params!r}, "
            f"pdu_conf={self.pdu_file_directive.pdu_conf!r})"
        )

    def __hash__(self) -> int:
        return hash((self.pdu_file_directive, self._params))
