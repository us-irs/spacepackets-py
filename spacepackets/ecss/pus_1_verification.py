# -*- coding: utf-8 -*-
"""ECSS PUS Service 1 Verification"""
from __future__ import annotations

import enum
import struct
from dataclasses import dataclass
from typing import Optional

from spacepackets.ccsds.spacepacket import PacketId, PacketSeqCtrl, SpacePacketHeader
from spacepackets.ccsds.time import CdsShortTimestamp
from spacepackets.ecss import PusTelecommand
from spacepackets.ecss.conf import FETCH_GLOBAL_APID
from spacepackets.ecss.definitions import PusServices
from spacepackets.ecss.field import PacketFieldEnum
from spacepackets.ecss.tm import PusVersion, PusTelemetry
from spacepackets.log import get_console_logger


class Subservices(enum.IntEnum):
    INVALID = 0
    TM_ACCEPTANCE_SUCCESS = 1
    TM_ACCEPTANCE_FAILURE = 2
    TM_START_SUCCESS = 3
    TM_START_FAILURE = 4
    TM_STEP_SUCCESS = 5
    TM_STEP_FAILURE = 6
    TM_COMPLETION_SUCCESS = 7
    TM_COMPLETION_FAILURE = 8


class RequestId:
    def __init__(
        self, tc_packet_id: PacketId, tc_psc: PacketSeqCtrl, ccsds_version: int = 0b000
    ):
        self.tc_packet_id = tc_packet_id
        self.tc_psc = tc_psc
        self.ccsds_version = ccsds_version

    @classmethod
    def empty(cls):
        return cls(PacketId.empty(), PacketSeqCtrl.empty())

    @classmethod
    def unpack(cls, tm_data: bytes) -> RequestId:
        if len(tm_data) < 4:
            raise ValueError(
                "Given Raw TM data too small to parse Request ID. Must be 4 bytes at least"
            )
        packet_id_version_raw = struct.unpack("!H", tm_data[0:2])[0]
        psc_raw = struct.unpack("!H", tm_data[2:4])[0]
        return cls(
            ccsds_version=(packet_id_version_raw >> 13) & 0b111,
            tc_packet_id=PacketId.from_raw(packet_id_version_raw),
            tc_psc=PacketSeqCtrl.from_raw(psc_raw),
        )

    @classmethod
    def from_sp_header(cls, header: SpacePacketHeader) -> RequestId:
        return cls(
            ccsds_version=header.ccsds_version,
            tc_packet_id=header.packet_id,
            tc_psc=header.psc,
        )

    def pack(self) -> bytes:
        raw = bytearray()
        packet_id_and_version = (self.ccsds_version << 13) | self.tc_packet_id.raw()
        raw.extend(struct.pack("!H", packet_id_and_version))
        raw.extend(struct.pack("!H", self.tc_psc.raw()))
        return raw


class FailureNotice:
    def __init__(self, code: PacketFieldEnum, data: bytes):
        if (code.pfc % 8) != 0:
            raise ValueError("PFC values for error code must be byte-aligned")
        elif round(code.pfc / 8) not in [1, 2, 4, 8]:
            raise ValueError("Allowed byte size for failure notice: 1, 2, 4 or 8")
        self.code = code
        self.data = data

    def pack(self) -> bytes:
        data = self.code.pack()
        data.extend(self.data)
        return data

    @classmethod
    def unpack(cls, data: bytes, num_bytes_err_code: int, num_bytes_data: int):
        pfc = num_bytes_err_code * 8
        return cls(
            code=PacketFieldEnum.unpack(data, pfc),
            data=data[num_bytes_err_code : num_bytes_err_code + num_bytes_data],
        )


@dataclass
class UnpackParams:
    bytes_step_id: int = 1
    bytes_err_code: int = 1


@dataclass
class VerificationParams:
    req_id: RequestId
    step_id: Optional[PacketFieldEnum] = None
    failure_notice: Optional[FailureNotice] = None

    def pack(self, pack_step_id: bool, pack_failure_notice: bool) -> bytearray:
        data = bytearray(self.req_id.pack())
        if self.step_id is not None and pack_step_id:
            self.step_id.pack()
        if pack_failure_notice:
            data.extend(self.failure_notice.pack())
        return data


class Service1Tm:
    """Service 1 TM class representation"""

    def __init__(
        self,
        subservice: Subservices,
        verif_params: Optional[VerificationParams] = None,
        time: CdsShortTimestamp = None,
        seq_count: int = 0,
        apid: int = FETCH_GLOBAL_APID,
        packet_version: int = 0b000,
        pus_version: PusVersion = PusVersion.GLOBAL_CONFIG,
        secondary_header_flag: bool = True,
        space_time_ref: int = 0b0000,
        destination_id: int = 0,
    ):
        if verif_params is None:
            self._verif_params = VerificationParams(RequestId.empty())
        else:
            self._verif_params = verif_params
        self.pus_tm = PusTelemetry(
            service=PusServices.S1_VERIFICATION,
            subservice=subservice,
            time=time,
            seq_count=seq_count,
            apid=apid,
            packet_version=packet_version,
            secondary_header_flag=secondary_header_flag,
            space_time_ref=space_time_ref,
            destination_id=destination_id,
        )
        if verif_params is not None:
            self.pus_tm.tm_data = verif_params.pack(
                pack_step_id=self.is_step_reply,
                pack_failure_notice=self.has_failure_notice,
            )

    def pack(self) -> bytearray:
        return self.pus_tm.pack()

    @classmethod
    def __empty(cls) -> Service1Tm:
        return cls(subservice=Subservices.INVALID)

    @classmethod
    def unpack(cls, data: bytes, params: UnpackParams) -> Service1Tm:
        """Parse a service 1 telemetry packet

        :param params:
        :param data:
        :raises ValueError: Raw telemetry too short
        :return:
        """
        service_1_tm = cls.__empty()
        service_1_tm.pus_tm = PusTelemetry.unpack(raw_telemetry=data)
        cls._unpack_raw_tm(service_1_tm, params)
        return service_1_tm

    @property
    def subservice(self):
        return self.pus_tm.subservice

    @classmethod
    def _unpack_raw_tm(cls, instance: Service1Tm, params: UnpackParams):
        tm_data = instance.pus_tm.tm_data
        if len(tm_data) < 4:
            raise ValueError("TM data less than 4 bytes")
        instance.tc_req_id = RequestId.unpack(tm_data[0:4])
        if instance.pus_tm.subservice % 2 == 0:
            instance._unpack_failure_verification(params)
        else:
            instance._unpack_success_verification(params)

    def _unpack_failure_verification(self, unpack_cfg: UnpackParams):
        """Handle parsing a verification failure packet, subservice ID 2, 4, 6 or 8"""
        tm_data = self.pus_tm.tm_data
        subservice = self.pus_tm.subservice
        expected_len = unpack_cfg.bytes_err_code
        if subservice == 6:
            expected_len += unpack_cfg.bytes_step_id
        elif subservice not in [2, 4, 8]:
            logger = get_console_logger()
            logger.error("Service1TM: Invalid subservice")
        if len(tm_data) < expected_len:
            raise ValueError(
                f"PUS TM[1,{subservice}] source data with length {len(tm_data)} smaller than "
                f"expected {expected_len} bytes"
            )
        current_idx = 4
        if self.is_step_reply:
            self._verif_params.step_id = PacketFieldEnum.unpack(
                tm_data[current_idx:], unpack_cfg.bytes_step_id
            )
            current_idx += unpack_cfg.bytes_step_id
        self._verif_params.failure_notice = FailureNotice.unpack(
            tm_data[current_idx:], unpack_cfg.bytes_err_code, len(tm_data) - current_idx
        )

    def _unpack_success_verification(self, unpack_cfg: UnpackParams):
        if self.pus_tm.subservice == 5:
            self._verif_params.step_number = PacketFieldEnum.unpack(
                self.pus_tm.tm_data[0 : unpack_cfg.bytes_step_id],
                pfc=unpack_cfg.bytes_step_id * 8,
            )
        elif self.pus_tm.subservice not in [1, 3, 7]:
            logger = get_console_logger()
            logger.warning("Service1TM: Invalid subservice")

    @property
    def failure_notice(self) -> Optional[FailureNotice]:
        return self._verif_params.failure_notice

    @property
    def has_failure_notice(self) -> bool:
        return (self.subservice % 2) == 0

    @property
    def tc_req_id(self):
        return self._verif_params.req_id

    @tc_req_id.setter
    def tc_req_id(self, value):
        self._verif_params.req_id = value

    @property
    def error_code(self) -> Optional[PacketFieldEnum]:
        if self.has_failure_notice:
            return self._verif_params.failure_notice.code
        else:
            return None

    @property
    def is_step_reply(self) -> bool:
        return (
            self.subservice == Subservices.TM_STEP_FAILURE
            or self.subservice == Subservices.TM_STEP_SUCCESS
        )

    @property
    def step_id(self) -> Optional[PacketFieldEnum]:
        """Retrieve the step number. Returns NONE if this packet does not have a step ID"""
        return self._verif_params.step_id


def create_acceptance_success_tm(pus_tc: PusTelecommand) -> Service1Tm:
    return Service1Tm(
        subservice=Subservices.TM_ACCEPTANCE_SUCCESS,
        verif_params=VerificationParams(RequestId.from_sp_header(pus_tc.sp_header)),
    )


def create_acceptance_failure_tm(
    pus_tc: PusTelecommand, failure_notice: FailureNotice
) -> Service1Tm:
    return Service1Tm(
        subservice=Subservices.TM_ACCEPTANCE_FAILURE,
        verif_params=VerificationParams(
            req_id=RequestId.from_sp_header(pus_tc.sp_header),
            failure_notice=failure_notice,
        ),
    )


def create_start_success_tm(pus_tc: PusTelecommand) -> Service1Tm:
    return Service1Tm(
        subservice=Subservices.TM_START_SUCCESS,
        verif_params=VerificationParams(RequestId.from_sp_header(pus_tc.sp_header)),
    )


def create_start_failure_tm(
    pus_tc: PusTelecommand, failure_notice: FailureNotice
) -> Service1Tm:
    return Service1Tm(
        subservice=Subservices.TM_START_FAILURE,
        verif_params=VerificationParams(
            req_id=RequestId.from_sp_header(pus_tc.sp_header),
            failure_notice=failure_notice,
        ),
    )


def create_step_success_tm(
    pus_tc: PusTelecommand, step_id: PacketFieldEnum
) -> Service1Tm:
    return Service1Tm(
        subservice=Subservices.TM_STEP_SUCCESS,
        verif_params=VerificationParams(
            req_id=RequestId.from_sp_header(pus_tc.sp_header), step_id=step_id
        ),
    )


def create_step_failure_tm(
    pus_tc: PusTelecommand, step_id: PacketFieldEnum, failure_notice: FailureNotice
) -> Service1Tm:
    return Service1Tm(
        subservice=Subservices.TM_STEP_FAILURE,
        verif_params=VerificationParams(
            req_id=RequestId.from_sp_header(pus_tc.sp_header),
            step_id=step_id,
            failure_notice=failure_notice,
        ),
    )


def create_completion_success_tm(pus_tc: PusTelecommand) -> Service1Tm:
    return Service1Tm(
        subservice=Subservices.TM_COMPLETION_SUCCESS,
        verif_params=VerificationParams(RequestId.from_sp_header(pus_tc.sp_header)),
    )


def create_completion_failure_tm(
    pus_tc: PusTelecommand, failure_notice: FailureNotice
) -> Service1Tm:
    return Service1Tm(
        subservice=Subservices.TM_COMPLETION_FAILURE,
        verif_params=VerificationParams(
            req_id=RequestId.from_sp_header(pus_tc.sp_header),
            failure_notice=failure_notice,
        ),
    )
