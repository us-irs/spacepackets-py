from typing import Optional, List
from unittest import TestCase

from spacepackets.ccsds import CdsShortTimestamp
from spacepackets.ecss import PusTelecommand
from spacepackets.ecss.pus_1_verification import (
    create_acceptance_success_tm,
    RequestId,
    create_start_success_tm,
    create_step_success_tm,
    StepId,
    create_completion_success_tm,
    FailureNotice,
    create_acceptance_failure_tm,
    create_start_failure_tm,
    create_step_failure_tm,
    create_completion_failure_tm,
    ErrorCode,
)
from spacepackets.ecss.pus_verificator import (
    PusVerificator,
    StatusField,
    VerificationStatus,
)


class SuccessSet:
    def __init__(self, pus_tc: PusTelecommand):
        self.pus_tc = pus_tc
        self.req_id = RequestId.from_pus_tc(pus_tc)
        self.time_reader = CdsShortTimestamp.empty()
        self.acc_suc_tm = create_acceptance_success_tm(pus_tc, self.time_reader)
        self.sta_suc_tm = create_start_success_tm(pus_tc, self.time_reader)
        self.ste_suc_tm = create_step_success_tm(
            pus_tc=pus_tc,
            step_id=StepId.with_byte_size(1, 1),
            time_provider=self.time_reader,
        )
        self.fin_suc_tm = create_completion_success_tm(
            pus_tc, CdsShortTimestamp.empty()
        )


class FailureSet:
    def __init__(self, pus_tc: PusTelecommand, failure_notice: FailureNotice):
        self.suc_set = SuccessSet(pus_tc)
        self.failure_notice = failure_notice
        self.acc_fail_tm = create_acceptance_failure_tm(
            pus_tc, self.failure_notice, CdsShortTimestamp.empty()
        )
        self.sta_fail_tm = create_start_failure_tm(
            pus_tc, self.failure_notice, CdsShortTimestamp.empty()
        )
        self.ste_fail_tm = create_step_failure_tm(
            pus_tc,
            failure_notice=self.failure_notice,
            step_id=StepId.with_byte_size(1, 1),
            time_provider=CdsShortTimestamp.empty(),
        )
        self.fin_fail_tm = create_completion_failure_tm(
            failure_notice=self.failure_notice,
            pus_tc=self.suc_set.pus_tc,
            time_provider=CdsShortTimestamp.empty(),
        )

    @property
    def pus_tc(self):
        return self.suc_set.pus_tc

    @property
    def req_id(self):
        return self.suc_set.req_id


class TestPusVerificator(TestCase):
    def setUp(self) -> None:
        self.pus_verificator = PusVerificator()

    def test_basic(self):
        suc_set = SuccessSet(PusTelecommand(service=17, subservice=1))
        self.pus_verificator.add_tc(suc_set.pus_tc)
        check_res = self.pus_verificator.add_tm(suc_set.acc_suc_tm)
        self.assertEqual(check_res.completed, False)
        status = check_res.status
        self._check_status(
            status,
            False,
            StatusField.SUCCESS,
            StatusField.UNSET,
            StatusField.UNSET,
            [],
            StatusField.UNSET,
        )
        verif_dict = self.pus_verificator.verif_dict
        self.assertEqual(len(verif_dict), 1)
        for key, val in verif_dict.items():
            self.assertEqual(key, suc_set.req_id)
            self._check_status(
                val,
                False,
                StatusField.SUCCESS,
                StatusField.UNSET,
                StatusField.UNSET,
                [],
                StatusField.UNSET,
            )

    def test_complete_verification_clear_completed(self):
        self._regular_success_seq(SuccessSet(PusTelecommand(service=17, subservice=1)))
        self.pus_verificator.remove_completed_entries()
        self.assertEqual(len(self.pus_verificator.verif_dict), 0)

    def test_complete_verification_clear_completed_multi(self):
        self._regular_success_seq(
            SuccessSet(PusTelecommand(service=17, subservice=1, seq_count=0))
        )
        self._regular_success_seq(
            SuccessSet(PusTelecommand(service=5, subservice=4, seq_count=1))
        )
        self.pus_verificator.remove_completed_entries()
        self.assertEqual(len(self.pus_verificator.verif_dict), 0)

    def test_complete_verification_remove_manually(self):
        suc_set = SuccessSet(PusTelecommand(service=17, subservice=1))
        self._regular_success_seq(suc_set)
        self.assertTrue(self.pus_verificator.remove_entry(suc_set.req_id))
        self.assertEqual(len(self.pus_verificator.verif_dict), 0)

    def test_complete_verification_multi_remove_manually(self):
        set_0 = SuccessSet(PusTelecommand(service=17, subservice=1, seq_count=0))
        self._regular_success_seq(set_0)
        set_1 = SuccessSet(PusTelecommand(service=5, subservice=4, seq_count=1))
        self._regular_success_seq(set_1)
        self.assertTrue(self.pus_verificator.remove_entry(set_0.req_id))
        self.assertEqual(len(self.pus_verificator.verif_dict), 1)
        self.assertTrue(self.pus_verificator.remove_entry(set_1.req_id))
        self.assertEqual(len(self.pus_verificator.verif_dict), 0)

    def test_acceptance_failure(self):
        notice = FailureNotice(ErrorCode.with_byte_size(1, 8), data=bytes([0, 1]))
        fail_set = FailureSet(
            PusTelecommand(service=17, subservice=1, seq_count=0), notice
        )
        self.assertTrue(self.pus_verificator.add_tc(fail_set.pus_tc))
        status = self.pus_verificator.add_tm(fail_set.acc_fail_tm)
        self.assertIsNotNone(status)
        self.assertTrue(status.completed)
        self._check_status(
            status.status,
            True,
            StatusField.FAILURE,
            StatusField.UNSET,
            StatusField.UNSET,
            [],
            StatusField.UNSET,
        )

    def test_step_failure(self):
        notice = FailureNotice(ErrorCode.with_byte_size(1, 8), data=bytes([0, 1]))
        fail_set = FailureSet(
            PusTelecommand(service=17, subservice=1, seq_count=0), notice
        )
        self.assertTrue(self.pus_verificator.add_tc(fail_set.pus_tc))
        status = self.pus_verificator.add_tm(fail_set.suc_set.acc_suc_tm)
        self.assertIsNotNone(status)
        self.assertFalse(status.completed)
        self._check_status(
            status.status,
            False,
            StatusField.SUCCESS,
            StatusField.UNSET,
            StatusField.UNSET,
            [],
            StatusField.UNSET,
        )
        status = self.pus_verificator.add_tm(fail_set.suc_set.sta_suc_tm)
        self.assertFalse(status.completed)
        self.assertIsNotNone(status)
        self._check_status(
            status.status,
            False,
            StatusField.SUCCESS,
            StatusField.SUCCESS,
            StatusField.UNSET,
            [],
            StatusField.UNSET,
        )
        status = self.pus_verificator.add_tm(fail_set.ste_fail_tm)
        self.assertIsNotNone(status)
        self.assertTrue(status.completed)
        self._check_status(
            status.status,
            True,
            StatusField.SUCCESS,
            StatusField.SUCCESS,
            StatusField.FAILURE,
            [1],
            StatusField.UNSET,
        )

    def _regular_success_seq(self, suc_set: SuccessSet):
        self.assertTrue(self.pus_verificator.add_tc(suc_set.pus_tc))
        check_res = self.pus_verificator.add_tm(suc_set.acc_suc_tm)
        self.assertIsNotNone(check_res)
        status = check_res.status
        self._check_status(
            status,
            False,
            StatusField.SUCCESS,
            StatusField.UNSET,
            StatusField.UNSET,
            [],
            StatusField.UNSET,
        )
        check_res = self.pus_verificator.add_tm(suc_set.sta_suc_tm)
        self.assertIsNotNone(check_res)
        status = check_res.status
        self._check_status(
            status,
            False,
            StatusField.SUCCESS,
            StatusField.SUCCESS,
            StatusField.UNSET,
            [],
            StatusField.UNSET,
        )
        check_res = self.pus_verificator.add_tm(suc_set.ste_suc_tm)
        self.assertIsNotNone(check_res)
        status = check_res.status
        self._check_status(
            status,
            False,
            StatusField.SUCCESS,
            StatusField.SUCCESS,
            StatusField.SUCCESS,
            [1],
            StatusField.UNSET,
        )
        check_res = self.pus_verificator.add_tm(suc_set.fin_suc_tm)
        self.assertIsNotNone(check_res)
        status = check_res.status
        self._check_status(
            status,
            True,
            StatusField.SUCCESS,
            StatusField.SUCCESS,
            StatusField.SUCCESS,
            [1],
            StatusField.SUCCESS,
        )

    def _check_status(
        self,
        status: Optional[VerificationStatus],
        all_verifs: bool,
        acc_st: StatusField,
        sta_st: StatusField,
        step_st: StatusField,
        step_list: List[int],
        fin_st: StatusField,
    ):
        self.assertIsNotNone(status)
        self.assertEqual(status.all_verifs_recvd, all_verifs)
        self.assertEqual(status.accepted, acc_st)
        self.assertEqual(status.step, step_st)
        self.assertEqual(status.step_list, step_list)
        self.assertEqual(status.started, sta_st)
        self.assertEqual(status.completed, fin_st)
