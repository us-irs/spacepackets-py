# -*- coding: utf-8 -*-
"""ECSS PUS Service 1 Verification"""
from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Optional

from spacepackets.ccsds import SpacePacketHeader
from spacepackets.ccsds.time import CcsdsTimeProvider
from spacepackets.ecss import PusTelecommand
from spacepackets.ecss.conf import FETCH_GLOBAL_APID
from spacepackets.ecss.defs import PusService
from spacepackets.ecss.fields import PacketFieldEnum
from spacepackets.ecss.tm import PusTelemetry, AbstractPusTm
from .exceptions import TmSrcDataTooShortError

from .req_id import RequestId
from .. import BytesTooShortError


class Subservice(enum.IntEnum):
    INVALID = 0
    TM_ACCEPTANCE_SUCCESS = 1
    TM_ACCEPTANCE_FAILURE = 2
    TM_START_SUCCESS = 3
    TM_START_FAILURE = 4
    TM_STEP_SUCCESS = 5
    TM_STEP_FAILURE = 6
    TM_COMPLETION_SUCCESS = 7
    TM_COMPLETION_FAILURE = 8


ErrorCode = PacketFieldEnum


class FailureNotice:
    def __init__(self, code: ErrorCode, data: bytes):
        # The PFC of the passed error code is already checked for validity.
        self.code = code
        self.data = data

    def pack(self) -> bytes:
        data = self.code.pack()
        data.extend(self.data)
        return data

    def len(self):
        return self.code.len() + len(self.data)

    @classmethod
    def unpack(
        cls, data: bytes, num_bytes_err_code: int, num_bytes_data: Optional[int] = None
    ):
        pfc = num_bytes_err_code * 8
        if num_bytes_data is None:
            num_bytes_data = len(data) - num_bytes_err_code
        return cls(
            code=PacketFieldEnum.unpack(data, pfc),
            data=data[num_bytes_err_code : num_bytes_err_code + num_bytes_data],
        )

    def __repr__(self):
        return f"{self.__class__.__name__}(code={self.code!r}, data={self.data!r})"


@dataclass
class UnpackParams:
    time_reader: Optional[CcsdsTimeProvider]
    bytes_step_id: int = 1
    bytes_err_code: int = 1


StepId = PacketFieldEnum


@dataclass
class VerificationParams:
    req_id: RequestId
    step_id: Optional[StepId] = None
    failure_notice: Optional[FailureNotice] = None

    def pack(self) -> bytearray:
        data = bytearray(self.req_id.pack())
        if self.step_id is not None:
            data.extend(self.step_id.pack())
        if self.failure_notice is not None:
            data.extend(self.failure_notice.pack())
        return data

    def len(self):
        init_len = 4
        if self.step_id is not None:
            init_len += self.step_id.len()
        if self.failure_notice is not None:
            init_len += self.failure_notice.len()
        return init_len

    def verify_against_subservice(self, subservice: Subservice):
        if subservice % 2 == 0:
            if self.failure_notice is None:
                raise InvalidVerifParams("Failure Notice should be something")
            if subservice == Subservice.TM_STEP_FAILURE and self.step_id is None:
                raise InvalidVerifParams("Step ID should be something")
            elif subservice != Subservice.TM_STEP_FAILURE and self.step_id is not None:
                raise InvalidVerifParams("Step ID should be empty")
        else:
            if self.failure_notice is not None:
                raise InvalidVerifParams("Failure Notice should be empty")
            if subservice == Subservice.TM_STEP_SUCCESS and self.step_id is None:
                raise InvalidVerifParams("Step ID should be something")
            elif subservice != Subservice.TM_STEP_SUCCESS and self.step_id is not None:
                raise InvalidVerifParams("Step ID should be empty")


class InvalidVerifParams(Exception):
    pass


class Service1Tm(AbstractPusTm):
    """Service 1 TM class representation."""

    def __init__(
        self,
        subservice: Subservice,
        time_provider: Optional[CcsdsTimeProvider],
        verif_params: Optional[VerificationParams] = None,
        seq_count: int = 0,
        apid: int = FETCH_GLOBAL_APID,
        packet_version: int = 0b000,
        space_time_ref: int = 0b0000,
        destination_id: int = 0,
    ):
        if verif_params is None:
            self._verif_params = VerificationParams(RequestId.empty())
        else:
            self._verif_params = verif_params
        self.pus_tm = PusTelemetry(
            service=PusService.S1_VERIFICATION,
            subservice=subservice,
            time_provider=time_provider,
            seq_count=seq_count,
            apid=apid,
            packet_version=packet_version,
            space_time_ref=space_time_ref,
            destination_id=destination_id,
        )
        if verif_params is not None:
            verif_params.verify_against_subservice(subservice)
            self.pus_tm.tm_data = verif_params.pack()

    def pack(self) -> bytearray:
        return self.pus_tm.pack()

    @classmethod
    def __empty(cls, time_provider: Optional[CcsdsTimeProvider]) -> Service1Tm:
        return cls(subservice=Subservice.INVALID, time_provider=time_provider)

    @classmethod
    def from_tm(cls, tm: PusTelemetry, params: UnpackParams) -> Service1Tm:
        service_1_tm = cls.__empty(params.time_reader)
        service_1_tm.pus_tm = tm
        cls._unpack_raw_tm(service_1_tm, params)
        return service_1_tm

    @classmethod
    def unpack(cls, data: bytes, params: UnpackParams) -> Service1Tm:
        """Parse a service 1 telemetry packet.

        :param params:
        :param data:
        :raises ValueError: Subservice invalid.
        :raises BytesTooShortError: passed data too short
        :raises TmSourceDataTooShortError: TM source data too short.
        :return:
        """
        service_1_tm = cls.__empty(params.time_reader)
        service_1_tm.pus_tm = PusTelemetry.unpack(
            data=data, time_reader=params.time_reader
        )
        cls._unpack_raw_tm(service_1_tm, params)
        return service_1_tm

    @property
    def time_provider(self) -> Optional[CcsdsTimeProvider]:
        return self.pus_tm.time_provider

    @property
    def sp_header(self) -> SpacePacketHeader:
        return self.pus_tm.space_packet_header

    @property
    def service(self):
        return self.pus_tm.service

    @property
    def subservice(self):
        return self.pus_tm.subservice

    @property
    def source_data(self) -> bytes:
        return self.pus_tm.source_data

    @classmethod
    def _unpack_raw_tm(cls, instance: Service1Tm, params: UnpackParams):
        tm_data = instance.pus_tm.tm_data
        if len(tm_data) < 4:
            raise TmSrcDataTooShortError(4, len(tm_data))
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
            raise ValueError(f"invalid subservice {subservice}")
        if len(tm_data) < expected_len:
            raise TmSrcDataTooShortError(expected_len, len(tm_data))
        current_idx = 4
        if self.is_step_reply:
            self._verif_params.step_id = PacketFieldEnum.unpack(
                tm_data[current_idx:], unpack_cfg.bytes_step_id * 8
            )
            current_idx += unpack_cfg.bytes_step_id
        self._verif_params.failure_notice = FailureNotice.unpack(
            tm_data[current_idx:], unpack_cfg.bytes_err_code, len(tm_data) - current_idx
        )

    def _unpack_success_verification(self, unpack_cfg: UnpackParams):
        if self.pus_tm.subservice == Subservice.TM_STEP_SUCCESS:
            try:
                self._verif_params.step_id = StepId.unpack(
                    pfc=unpack_cfg.bytes_step_id * 8,
                    data=self.pus_tm.tm_data[4 : 4 + unpack_cfg.bytes_step_id],
                )
            except BytesTooShortError as e:
                raise TmSrcDataTooShortError(e.expected_len, e.bytes_len)
        elif self.pus_tm.subservice not in [1, 3, 7]:
            raise ValueError(
                f"invalid subservice {self.pus_tm.subservice}, not in [1, 3, 7]"
            )

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
    def error_code(self) -> Optional[ErrorCode]:
        if self.has_failure_notice:
            return self._verif_params.failure_notice.code
        else:
            return None

    @property
    def is_step_reply(self) -> bool:
        return (
            self.subservice == Subservice.TM_STEP_FAILURE
            or self.subservice == Subservice.TM_STEP_SUCCESS
        )

    @property
    def step_id(self) -> Optional[StepId]:
        """Retrieve the step number. Returns NONE if this packet does not have a step ID"""
        return self._verif_params.step_id

    def __eq__(self, other: Service1Tm):
        return (self.pus_tm == other.pus_tm) and (
            self._verif_params == other._verif_params
        )


def create_acceptance_success_tm(
    pus_tc: PusTelecommand, time_provider: Optional[CcsdsTimeProvider]
) -> Service1Tm:
    return Service1Tm(
        subservice=Subservice.TM_ACCEPTANCE_SUCCESS,
        verif_params=VerificationParams(RequestId.from_sp_header(pus_tc.sp_header)),
        time_provider=time_provider,
    )


def create_acceptance_failure_tm(
    pus_tc: PusTelecommand,
    failure_notice: FailureNotice,
    time_provider: Optional[CcsdsTimeProvider],
) -> Service1Tm:
    return Service1Tm(
        subservice=Subservice.TM_ACCEPTANCE_FAILURE,
        verif_params=VerificationParams(
            req_id=RequestId.from_sp_header(pus_tc.sp_header),
            failure_notice=failure_notice,
        ),
        time_provider=time_provider,
    )


def create_start_success_tm(
    pus_tc: PusTelecommand, time_provider: Optional[CcsdsTimeProvider]
) -> Service1Tm:
    return Service1Tm(
        subservice=Subservice.TM_START_SUCCESS,
        verif_params=VerificationParams(RequestId.from_sp_header(pus_tc.sp_header)),
        time_provider=time_provider,
    )


def create_start_failure_tm(
    pus_tc: PusTelecommand,
    failure_notice: FailureNotice,
    time_provider: Optional[CcsdsTimeProvider],
) -> Service1Tm:
    return Service1Tm(
        subservice=Subservice.TM_START_FAILURE,
        verif_params=VerificationParams(
            req_id=RequestId.from_sp_header(pus_tc.sp_header),
            failure_notice=failure_notice,
        ),
        time_provider=time_provider,
    )


def create_step_success_tm(
    pus_tc: PusTelecommand,
    step_id: PacketFieldEnum,
    time_provider: Optional[CcsdsTimeProvider],
) -> Service1Tm:
    return Service1Tm(
        subservice=Subservice.TM_STEP_SUCCESS,
        verif_params=VerificationParams(
            req_id=RequestId.from_sp_header(pus_tc.sp_header), step_id=step_id
        ),
        time_provider=time_provider,
    )


def create_step_failure_tm(
    pus_tc: PusTelecommand,
    step_id: PacketFieldEnum,
    failure_notice: FailureNotice,
    time_provider: Optional[CcsdsTimeProvider],
) -> Service1Tm:
    return Service1Tm(
        subservice=Subservice.TM_STEP_FAILURE,
        verif_params=VerificationParams(
            req_id=RequestId.from_sp_header(pus_tc.sp_header),
            step_id=step_id,
            failure_notice=failure_notice,
        ),
        time_provider=time_provider,
    )


def create_completion_success_tm(
    pus_tc: PusTelecommand, time_provider: Optional[CcsdsTimeProvider]
) -> Service1Tm:
    return Service1Tm(
        subservice=Subservice.TM_COMPLETION_SUCCESS,
        verif_params=VerificationParams(RequestId.from_sp_header(pus_tc.sp_header)),
        time_provider=time_provider,
    )


def create_completion_failure_tm(
    pus_tc: PusTelecommand,
    failure_notice: FailureNotice,
    time_provider: Optional[CcsdsTimeProvider],
) -> Service1Tm:
    return Service1Tm(
        subservice=Subservice.TM_COMPLETION_FAILURE,
        verif_params=VerificationParams(
            req_id=RequestId.from_sp_header(pus_tc.sp_header),
            failure_notice=failure_notice,
        ),
        time_provider=time_provider,
    )
