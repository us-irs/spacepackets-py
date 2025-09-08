"""ECSS PUS Service 1 Verification"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import TYPE_CHECKING

from spacepackets import BytesTooShortError
from spacepackets.ecss.defs import PusService
from spacepackets.ecss.fields import PacketFieldEnum
from spacepackets.ecss.tm import AbstractPusTm, ManagedParams, MiscParams, PusTm

from .exceptions import TmSrcDataTooShortError
from .req_id import RequestId

if TYPE_CHECKING:
    from spacepackets.ccsds import SpacePacketHeader
    from spacepackets.ccsds.spacepacket import PacketId, PacketSeqCtrl
    from spacepackets.ecss.tc import PusTc


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
        return bytes(data)

    def len(self) -> int:
        return self.code.len() + len(self.data)

    @classmethod
    def unpack(
        cls,
        data: bytes | bytearray,
        num_bytes_err_code: int,
        num_bytes_data: int | None = None,
    ) -> FailureNotice:
        pfc = num_bytes_err_code * 8
        if num_bytes_data is None:
            num_bytes_data = len(data) - num_bytes_err_code
        return cls(
            code=PacketFieldEnum.unpack(data, pfc),
            data=bytes(data[num_bytes_err_code : num_bytes_err_code + num_bytes_data]),
        )

    def __repr__(self):
        return f"{self.__class__.__name__}(code={self.code!r}, data={self.data!r})"


@dataclass
class ManagedParamsVerification:
    bytes_step_id: int = 1
    bytes_err_code: int = 1


StepId = PacketFieldEnum


@dataclass
class VerificationParams:
    req_id: RequestId
    step_id: StepId | None = None
    failure_notice: FailureNotice | None = None

    def pack(self) -> bytearray:
        data = bytearray(self.req_id.pack())
        if self.step_id is not None:
            data.extend(self.step_id.pack())
        if self.failure_notice is not None:
            data.extend(self.failure_notice.pack())
        return data

    def len(self) -> int:
        init_len = 4
        if self.step_id is not None:
            init_len += self.step_id.len()
        if self.failure_notice is not None:
            init_len += self.failure_notice.len()
        return init_len

    def verify_against_subservice(self, subservice: Subservice) -> None:
        if subservice % 2 == 0:
            if self.failure_notice is None:
                raise InvalidVerifParamsError("Failure Notice should be something")
            if subservice == Subservice.TM_STEP_FAILURE and self.step_id is None:
                raise InvalidVerifParamsError("Step ID should be something")
            if subservice != Subservice.TM_STEP_FAILURE and self.step_id is not None:
                raise InvalidVerifParamsError("Step ID should be empty")
        else:
            if self.failure_notice is not None:
                raise InvalidVerifParamsError("Failure Notice should be empty")
            if subservice == Subservice.TM_STEP_SUCCESS and self.step_id is None:
                raise InvalidVerifParamsError("Step ID should be something")
            if subservice != Subservice.TM_STEP_SUCCESS and self.step_id is not None:
                raise InvalidVerifParamsError("Step ID should be empty")


class InvalidVerifParamsError(Exception):
    pass


class Service1Tm(AbstractPusTm):
    """Service 1 TM class representation."""

    def __init__(
        self,
        apid: int,
        subservice: Subservice,
        timestamp: bytes | bytearray,
        verif_params: VerificationParams | None = None,
        seq_count: int = 0,
        destination_id: int = 0,
        misc_params: MiscParams | None = None,
    ):
        if verif_params is None:
            self._verif_params = VerificationParams(RequestId.empty())
        else:
            self._verif_params = verif_params
        self.pus_tm = PusTm(
            service=PusService.S1_VERIFICATION,
            subservice=subservice,
            timestamp=timestamp,
            seq_count=seq_count,
            apid=apid,
            destination_id=destination_id,
            misc_params=misc_params,
        )
        if verif_params is not None:
            verif_params.verify_against_subservice(subservice)
            self.pus_tm.tm_data = bytes(verif_params.pack())

    def pack(self) -> bytearray:
        return self.pus_tm.pack()

    def __hash__(self) -> int:
        return hash(self.pus_tm)

    @classmethod
    def __empty(cls) -> Service1Tm:
        return cls(apid=0, subservice=Subservice.INVALID, timestamp=b"")

    @classmethod
    def from_tm(cls, tm: PusTm, verif_params: ManagedParamsVerification) -> Service1Tm:
        service_1_tm = cls.__empty()
        service_1_tm.pus_tm = tm
        cls._unpack_raw_tm(service_1_tm, verif_params)
        return service_1_tm

    @classmethod
    def unpack(
        cls, data: bytes, managed_params: ManagedParams, verif_params: ManagedParamsVerification
    ) -> Service1Tm:
        """Parse a service 1 telemetry packet.

        :param params:
        :param data:
        :raises ValueError: Subservice invalid.
        :raises BytesTooShortError: passed data too short
        :raises TmSourceDataTooShortError: TM source data too short.
        :return:
        """
        service_1_tm = cls.__empty()
        service_1_tm.pus_tm = PusTm.unpack_generic(data=data, managed_params=managed_params)
        cls._unpack_raw_tm(service_1_tm, verif_params)
        return service_1_tm

    @property
    def timestamp(self) -> bytes:
        return self.pus_tm.timestamp

    @property
    def ccsds_version(self) -> int:
        return self.pus_tm.space_packet_header.ccsds_version

    @property
    def packet_seq_control(self) -> PacketSeqCtrl:
        return self.pus_tm.space_packet_header.packet_seq_control

    @property
    def packet_id(self) -> PacketId:
        return self.pus_tm.space_packet_header.packet_id

    @property
    def sp_header(self) -> SpacePacketHeader:
        return self.pus_tm.space_packet_header

    @property
    def service(self) -> int:
        return self.pus_tm.service

    @property
    def subservice(self) -> int:
        return self.pus_tm.subservice

    @property
    def source_data(self) -> bytes:
        return self.pus_tm.source_data

    @classmethod
    def _unpack_raw_tm(cls, instance: Service1Tm, params: ManagedParamsVerification) -> None:
        tm_data = instance.pus_tm.tm_data
        if len(tm_data) < 4:
            raise TmSrcDataTooShortError(4, len(tm_data))
        instance.tc_req_id = RequestId.unpack(tm_data[0:4])
        if instance.pus_tm.subservice % 2 == 0:
            instance._unpack_failure_verification(params)
        else:
            instance._unpack_success_verification(params)

    def _unpack_failure_verification(self, unpack_cfg: ManagedParamsVerification) -> None:
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

    def _unpack_success_verification(self, unpack_cfg: ManagedParamsVerification) -> None:
        if self.pus_tm.subservice == Subservice.TM_STEP_SUCCESS:
            try:
                self._verif_params.step_id = StepId.unpack(
                    pfc=unpack_cfg.bytes_step_id * 8,
                    data=self.pus_tm.tm_data[4 : 4 + unpack_cfg.bytes_step_id],
                )
            except BytesTooShortError as e:
                raise TmSrcDataTooShortError(e.expected_len, e.bytes_len) from e
        elif self.pus_tm.subservice not in [1, 3, 7]:
            raise ValueError(f"invalid subservice {self.pus_tm.subservice}, not in [1, 3, 7]")

    @property
    def failure_notice(self) -> FailureNotice | None:
        return self._verif_params.failure_notice

    @property
    def has_failure_notice(self) -> bool:
        return (self.subservice % 2) == 0

    @property
    def tc_req_id(self) -> RequestId:
        return self._verif_params.req_id

    @tc_req_id.setter
    def tc_req_id(self, value: RequestId) -> None:
        self._verif_params.req_id = value

    @property
    def error_code(self) -> ErrorCode | None:
        if self.has_failure_notice:
            assert self._verif_params.failure_notice is not None
            return self._verif_params.failure_notice.code
        return None

    @property
    def is_step_reply(self) -> bool:
        return self.subservice in (
            Subservice.TM_STEP_FAILURE,
            Subservice.TM_STEP_SUCCESS,
        )

    @property
    def step_id(self) -> StepId | None:
        """Retrieve the step number. Returns NONE if this packet does not have a step ID"""
        return self._verif_params.step_id

    def __eq__(self, other: object):
        if isinstance(other, Service1Tm):
            return (self.pus_tm == other.pus_tm) and (self._verif_params == other._verif_params)
        return False


def create_acceptance_success_tm(apid: int, pus_tc: PusTc, timestamp: bytes) -> Service1Tm:
    return Service1Tm(
        apid=apid,
        subservice=Subservice.TM_ACCEPTANCE_SUCCESS,
        verif_params=VerificationParams(RequestId.from_sp_header(pus_tc.sp_header)),
        timestamp=timestamp,
    )


def create_acceptance_failure_tm(
    apid: int,
    pus_tc: PusTc,
    failure_notice: FailureNotice,
    timestamp: bytes,
) -> Service1Tm:
    return Service1Tm(
        apid=apid,
        subservice=Subservice.TM_ACCEPTANCE_FAILURE,
        verif_params=VerificationParams(
            req_id=RequestId.from_sp_header(pus_tc.sp_header),
            failure_notice=failure_notice,
        ),
        timestamp=timestamp,
    )


def create_start_success_tm(apid: int, pus_tc: PusTc, timestamp: bytes) -> Service1Tm:
    return Service1Tm(
        apid=apid,
        subservice=Subservice.TM_START_SUCCESS,
        verif_params=VerificationParams(RequestId.from_sp_header(pus_tc.sp_header)),
        timestamp=timestamp,
    )


def create_start_failure_tm(
    apid: int,
    pus_tc: PusTc,
    failure_notice: FailureNotice,
    timestamp: bytes,
) -> Service1Tm:
    return Service1Tm(
        apid=apid,
        subservice=Subservice.TM_START_FAILURE,
        verif_params=VerificationParams(
            req_id=RequestId.from_sp_header(pus_tc.sp_header),
            failure_notice=failure_notice,
        ),
        timestamp=timestamp,
    )


def create_step_success_tm(
    apid: int,
    pus_tc: PusTc,
    step_id: PacketFieldEnum,
    timestamp: bytes,
) -> Service1Tm:
    return Service1Tm(
        apid=apid,
        subservice=Subservice.TM_STEP_SUCCESS,
        verif_params=VerificationParams(
            req_id=RequestId.from_sp_header(pus_tc.sp_header), step_id=step_id
        ),
        timestamp=timestamp,
    )


def create_step_failure_tm(
    apid: int,
    pus_tc: PusTc,
    step_id: PacketFieldEnum,
    failure_notice: FailureNotice,
    timestamp: bytes,
) -> Service1Tm:
    return Service1Tm(
        apid=apid,
        subservice=Subservice.TM_STEP_FAILURE,
        verif_params=VerificationParams(
            req_id=RequestId.from_sp_header(pus_tc.sp_header),
            step_id=step_id,
            failure_notice=failure_notice,
        ),
        timestamp=timestamp,
    )


def create_completion_success_tm(apid: int, pus_tc: PusTc, timestamp: bytes) -> Service1Tm:
    return Service1Tm(
        apid=apid,
        subservice=Subservice.TM_COMPLETION_SUCCESS,
        verif_params=VerificationParams(RequestId.from_sp_header(pus_tc.sp_header)),
        timestamp=timestamp,
    )


def create_completion_failure_tm(
    apid: int,
    pus_tc: PusTc,
    failure_notice: FailureNotice,
    timestamp: bytes,
) -> Service1Tm:
    return Service1Tm(
        apid=apid,
        subservice=Subservice.TM_COMPLETION_FAILURE,
        verif_params=VerificationParams(
            req_id=RequestId.from_sp_header(pus_tc.sp_header),
            failure_notice=failure_notice,
        ),
        timestamp=timestamp,
    )
