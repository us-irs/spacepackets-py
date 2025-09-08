from typing import Optional
from unittest import TestCase

from spacepackets import PacketType, SpacePacketHeader
from spacepackets.ccsds import CdsShortTimestamp
from spacepackets.ecss import PacketFieldEnum, PusTc, RequestId
from spacepackets.ecss.pus_1_verification import (
    ErrorCode,
    FailureNotice,
    ManagedParamsVerification,
    Service1Tm,
    StepId,
    Subservice,
    VerificationParams,
    create_acceptance_failure_tm,
    create_acceptance_success_tm,
    create_completion_failure_tm,
    create_completion_success_tm,
    create_start_failure_tm,
    create_start_success_tm,
    create_step_failure_tm,
    create_step_success_tm,
)
from spacepackets.ecss.tm import ManagedParams
from tests.ecss.common import TEST_STAMP


class Service1TmTest(TestCase):
    def setUp(self) -> None:
        self.def_apid = 0x02
        ping_tc = PusTc(apid=self.def_apid, service=17, subservice=1)
        self.srv1_tm = create_start_success_tm(
            apid=self.def_apid, pus_tc=ping_tc, timestamp=TEST_STAMP
        )

    def test_failure_notice_invalid_creation(self):
        with self.assertRaises(ValueError):
            FailureNotice(ErrorCode(pfc=4, val=2), b"")

    def test_basic(self):
        self.assertEqual(self.srv1_tm.sp_header, self.srv1_tm.pus_tm.space_packet_header)
        self.assertEqual(self.srv1_tm.timestamp, TEST_STAMP)
        self.assertEqual(self.srv1_tm.is_step_reply, False)
        self.assertEqual(self.srv1_tm.service, 1)
        self.assertEqual(self.srv1_tm.subservice, 3)
        self.assertEqual(self.srv1_tm.error_code, None)

    def test_other_ctor(self):
        srv1_tm = Service1Tm.from_tm(self.srv1_tm.pus_tm, ManagedParamsVerification())
        self.assertEqual(srv1_tm, self.srv1_tm)

    def test_failure_notice(self):
        error_code = PacketFieldEnum(pfc=8, val=2)
        failure_notice = FailureNotice(code=error_code, data=bytes([0, 2, 4, 8]))
        self.assertEqual(failure_notice.code.val, error_code.val)
        self.assertEqual(failure_notice.code.pfc, error_code.pfc)
        notice_raw = failure_notice.pack()
        notice_unpacked = FailureNotice.unpack(notice_raw, 1, 4)
        self.assertEqual(notice_unpacked.code.val, error_code.val)
        self.assertEqual(notice_unpacked.code.pfc, error_code.pfc)
        self.assertEqual(notice_unpacked.data, bytes([0, 2, 4, 8]))

    def test_verif_params(self):
        sp_header = SpacePacketHeader(
            packet_type=PacketType.TM,
            apid=0x22,
            sec_header_flag=False,
            seq_count=22,
            data_len=35,
        )
        verif_param = VerificationParams(req_id=RequestId.from_sp_header(sp_header))
        self.assertEqual(verif_param.len(), 4)
        verif_param.step_id = StepId(pfc=8, val=12)
        self.assertEqual(verif_param.len(), 5)
        verif_param.step_id.pfc = 16
        self.assertEqual(verif_param.len(), 6)
        verif_param.failure_notice = FailureNotice(
            code=ErrorCode(pfc=16, val=22), data=bytes([0, 1, 2])
        )
        self.assertEqual(verif_param.len(), 11)

    def test_service_1_tm_acc_success(self):
        self._generic_test_srv_1_success(Subservice.TM_ACCEPTANCE_SUCCESS)

    def test_service_1_tm_start_success(self):
        self._generic_test_srv_1_success(Subservice.TM_START_SUCCESS)

    def test_service_1_tm_step_success(self):
        self._generic_test_srv_1_success(Subservice.TM_STEP_SUCCESS)

    def test_service_1_tm_completion_success(self):
        self._generic_test_srv_1_success(Subservice.TM_COMPLETION_SUCCESS)

    def _generic_test_srv_1_success(self, subservice: Subservice):
        pus_tc = PusTc(apid=self.def_apid, service=17, subservice=1)
        helper_created = None
        step_id = None
        if subservice == Subservice.TM_ACCEPTANCE_SUCCESS:
            helper_created = create_acceptance_success_tm(
                apid=self.def_apid, pus_tc=pus_tc, timestamp=TEST_STAMP
            )
        elif subservice == Subservice.TM_START_SUCCESS:
            helper_created = create_start_success_tm(self.def_apid, pus_tc, TEST_STAMP)
        elif subservice == Subservice.TM_STEP_SUCCESS:
            step_id = PacketFieldEnum.with_byte_size(1, 4)
            helper_created = create_step_success_tm(self.def_apid, pus_tc, step_id, TEST_STAMP)
        elif subservice == Subservice.TM_COMPLETION_SUCCESS:
            helper_created = create_completion_success_tm(
                self.def_apid, pus_tc, timestamp=TEST_STAMP
            )
        self._test_srv_1_success_tm(
            pus_tc,
            Service1Tm(
                apid=self.def_apid,
                subservice=subservice,
                verif_params=VerificationParams(
                    req_id=RequestId(pus_tc.packet_id, pus_tc.packet_seq_control),
                    step_id=step_id,
                ),
                timestamp=CdsShortTimestamp.empty().pack(),
            ),
            subservice,
        )
        if helper_created is not None:
            self._test_srv_1_success_tm(pus_tc, helper_created, subservice, step_id)

    def test_service_1_tm_acceptance_failure(self):
        self._generic_test_srv_1_failure(Subservice.TM_ACCEPTANCE_FAILURE)

    def test_service_1_tm_start_failure(self):
        self._generic_test_srv_1_failure(Subservice.TM_START_FAILURE)

    def test_service_1_tm_step_failure(self):
        self._generic_test_srv_1_failure(Subservice.TM_STEP_FAILURE)

    def test_service_1_tm_completion_failure(self):
        self._generic_test_srv_1_failure(Subservice.TM_COMPLETION_FAILURE)

    def _test_srv_1_success_tm(
        self,
        pus_tc: PusTc,
        srv_1_tm: Service1Tm,
        subservice: Subservice,
        step_id: Optional[PacketFieldEnum] = None,
    ):
        self.assertEqual(srv_1_tm.pus_tm.subservice, subservice)
        self.assertEqual(srv_1_tm.tc_req_id.tc_packet_id, pus_tc.packet_id)
        self.assertEqual(srv_1_tm.tc_req_id.tc_psc, pus_tc.packet_seq_control)
        srv_1_tm_raw = srv_1_tm.pack()
        srv_1_tm_unpacked = Service1Tm.unpack(
            srv_1_tm_raw, ManagedParams(len(TEST_STAMP)), ManagedParamsVerification()
        )
        self.assertEqual(srv_1_tm_unpacked.tc_req_id.tc_packet_id.raw(), pus_tc.packet_id.raw())
        self.assertEqual(srv_1_tm_unpacked.tc_req_id.tc_psc.raw(), pus_tc.packet_seq_control.raw())
        if step_id is not None and subservice == Subservice.TM_STEP_SUCCESS:
            self.assertEqual(srv_1_tm_unpacked.step_id, step_id)

    def _generic_test_srv_1_failure(self, subservice: Subservice):
        pus_tc = PusTc(apid=self.def_apid, service=17, subservice=1)
        failure_notice = FailureNotice(
            code=PacketFieldEnum.with_byte_size(1, 8), data=bytes([2, 4])
        )
        helper_created = None
        step_id = None
        if subservice == Subservice.TM_ACCEPTANCE_FAILURE:
            helper_created = create_acceptance_failure_tm(
                self.def_apid, pus_tc, failure_notice, TEST_STAMP
            )
        elif subservice == Subservice.TM_START_FAILURE:
            helper_created = create_start_failure_tm(
                self.def_apid, pus_tc, failure_notice, TEST_STAMP
            )
        elif subservice == Subservice.TM_STEP_FAILURE:
            step_id = PacketFieldEnum.with_byte_size(2, 12)
            helper_created = create_step_failure_tm(
                self.def_apid,
                pus_tc,
                failure_notice=failure_notice,
                step_id=step_id,
                timestamp=TEST_STAMP,
            )
        elif subservice == Subservice.TM_COMPLETION_FAILURE:
            helper_created = create_completion_failure_tm(
                self.def_apid, pus_tc, failure_notice, TEST_STAMP
            )
        self._test_srv_1_failure_comparison_helper(
            pus_tc,
            Service1Tm(
                apid=self.def_apid,
                subservice=subservice,
                verif_params=VerificationParams(
                    req_id=RequestId(pus_tc.packet_id, pus_tc.packet_seq_control),
                    failure_notice=failure_notice,
                    step_id=step_id,
                ),
                timestamp=TEST_STAMP,
            ),
            subservice=subservice,
            failure_notice=failure_notice,
            step_id=step_id,
        )
        if helper_created is not None:
            self._test_srv_1_failure_comparison_helper(
                pus_tc=pus_tc,
                srv_1_tm=helper_created,
                failure_notice=failure_notice,
                subservice=subservice,
                step_id=step_id,
            )

    def _test_srv_1_failure_comparison_helper(
        self,
        pus_tc: PusTc,
        srv_1_tm: Service1Tm,
        subservice: Subservice,
        failure_notice: Optional[FailureNotice],
        step_id: Optional[PacketFieldEnum] = None,
    ):
        self.assertEqual(srv_1_tm.pus_tm.subservice, subservice)
        self.assertEqual(srv_1_tm.tc_req_id.tc_packet_id, pus_tc.packet_id)
        self.assertEqual(srv_1_tm.tc_req_id.tc_psc, pus_tc.packet_seq_control)
        srv_1_tm_raw = srv_1_tm.pack()
        unpack_params = ManagedParamsVerification()
        if failure_notice is not None:
            unpack_params.bytes_err_code = failure_notice.code.len()
        if step_id is not None:
            unpack_params.bytes_step_id = step_id.len()
        srv_1_tm_unpacked = Service1Tm.unpack(
            srv_1_tm_raw, ManagedParams(len(TEST_STAMP)), unpack_params
        )
        self.assertEqual(srv_1_tm_unpacked.error_code.val, failure_notice.code.val)
        self.assertEqual(srv_1_tm_unpacked.tc_req_id.tc_packet_id.raw(), pus_tc.packet_id.raw())
        self.assertEqual(srv_1_tm_unpacked.tc_req_id.tc_psc.raw(), pus_tc.packet_seq_control.raw())
        if failure_notice is not None:
            self.assertEqual(srv_1_tm_unpacked.failure_notice.pack(), failure_notice.pack())
        if step_id is not None:
            self.assertEqual(srv_1_tm_unpacked.step_id.pack(), step_id.pack())
