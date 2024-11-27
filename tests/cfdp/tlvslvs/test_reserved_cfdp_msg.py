import struct
from pathlib import Path
from unittest import TestCase

from spacepackets.cfdp import (
    CfdpLv,
    ConditionCode,
    DeliveryCode,
    FileStatus,
    FinishedParams,
    TransactionId,
    TransmissionMode,
)
from spacepackets.cfdp.tlv import (
    ORIGINATING_TRANSACTION_ID_MSG_TYPE_ID,
    DirectoryListingParameters,
    DirectoryListingRequest,
    DirectoryListingResponse,
    DirectoryOperationMessageType,
    DirectoryParams,
    DirListingOptions,
    MessageToUserTlv,
    OriginatingTransactionId,
    ProxyCancelRequest,
    ProxyClosureRequest,
    ProxyMessageType,
    ProxyPutRequest,
    ProxyPutRequestParams,
    ProxyPutResponse,
    ProxyPutResponseParams,
    ProxyTransmissionMode,
    TlvType,
)
from spacepackets.util import ByteFieldU8, ByteFieldU16


class TestReservedMsg(TestCase):
    def setUp(self) -> None:
        self.dest_entity_id = ByteFieldU8(5)
        self.src_string = "hello.txt"
        self.src_name = CfdpLv.from_str(self.src_string)
        self.dest_string = "hello2.txt"
        self.dest_name = CfdpLv.from_str(self.dest_string)
        self.proxy_put_req_params = ProxyPutRequestParams(
            self.dest_entity_id, self.src_name, self.dest_name
        )
        self.proxy_put_request = ProxyPutRequest(self.proxy_put_req_params)

        self.originating_id_source_id = ByteFieldU16(1)
        self.originating_id_seq_num = ByteFieldU16(5)
        self.originating_transaction_id = TransactionId(
            self.originating_id_source_id, self.originating_id_seq_num
        )
        self.originating_transaction_id_msg = OriginatingTransactionId(
            self.originating_transaction_id
        )

        self.proxy_put_response_params = ProxyPutResponseParams(
            ConditionCode.NO_ERROR, DeliveryCode.DATA_COMPLETE, FileStatus.FILE_RETAINED
        )
        self.proxy_put_response = ProxyPutResponse(self.proxy_put_response_params)
        self.proxy_closure_requested = ProxyClosureRequest(True)
        self.proxy_transmission_mode = ProxyTransmissionMode(TransmissionMode.UNACKNOWLEDGED)

        self.proxy_cancel_request = ProxyCancelRequest()

        self.dir_path_lv = CfdpLv.from_str("/tmp")
        self.dir_listing_name_lv = CfdpLv.from_str("/tmp/listing.txt")
        self.dir_params = DirectoryParams(self.dir_path_lv, self.dir_listing_name_lv)
        self.dir_listing_req = DirectoryListingRequest(self.dir_params)
        self.dir_listing_response = DirectoryListingResponse(True, self.dir_params)
        self.dir_lst_opt_recursive = True
        self.dir_lst_opt_all = True
        self.dir_listing_options = DirListingOptions(
            self.dir_lst_opt_recursive, self.dir_lst_opt_all
        )
        self.dir_listing_options_msg = DirectoryListingParameters(self.dir_listing_options)

    def _generic_raw_data_verification(
        self, data: bytes, expected_custom_len: int, expected_msg_type: int
    ):
        self.assertEqual(data[0], TlvType.MESSAGE_TO_USER)
        # Lenght must hold at least "cfdp" string and message type.
        self.assertTrue(data[1] >= 5)
        self.assertEqual(data[1], 5 + expected_custom_len)
        self.assertEqual(data[2:6].decode(), "cfdp")
        self.assertEqual(data[6], expected_msg_type)

    def test_proxy_put_request_state(self):
        self.assertTrue(self.proxy_put_request.is_cfdp_proxy_operation())
        self.assertFalse(self.proxy_put_request.is_directory_operation())
        self.assertFalse(self.proxy_put_request.is_originating_transaction_id())

    def test_proxy_put_req(self):
        self.assertEqual(
            self.proxy_put_request.get_proxy_put_request_params(),
            self.proxy_put_req_params,
        )
        self.assertEqual(
            self.proxy_put_request.get_reserved_cfdp_message_type(),
            ProxyMessageType.PUT_REQUEST,
        )
        self.assertEqual(
            self.proxy_put_request.get_cfdp_proxy_message_type(),
            ProxyMessageType.PUT_REQUEST,
        )
        raw = self.proxy_put_request.pack()
        self._generic_raw_data_verification(
            raw,
            # 2 bytes dest ID LV, and source and dest path LV.
            2 + 1 + len(self.src_string) + 1 + len(self.dest_string),
            ProxyMessageType.PUT_REQUEST,
        )

    def test_conversion_to_generic(self):
        msg_to_user = self.proxy_put_request.to_generic_msg_to_user_tlv()
        self.assertEqual(msg_to_user.tlv_type, TlvType.MESSAGE_TO_USER)

    def test_to_generic_and_to_reserved_again(self):
        msg_to_user = self.proxy_put_request.to_generic_msg_to_user_tlv()
        reserved_msg = msg_to_user.to_reserved_msg_tlv()
        self.assertIsNotNone(reserved_msg)
        self.assertEqual(self.proxy_put_request, reserved_msg)
        self.assertEqual(self.proxy_put_request.packet_len, reserved_msg.packet_len)

    def test_originating_transaction_id_state(self):
        self.assertTrue(self.originating_transaction_id_msg.is_originating_transaction_id())
        self.assertFalse(self.originating_transaction_id_msg.is_cfdp_proxy_operation())
        self.assertFalse(self.originating_transaction_id_msg.is_directory_operation())

    def test_originating_transaction_id_pack(self):
        raw_originating_id = self.originating_transaction_id_msg.pack()
        self._generic_raw_data_verification(
            raw_originating_id, 1 + 2 + 2, ORIGINATING_TRANSACTION_ID_MSG_TYPE_ID
        )
        self.assertEqual((raw_originating_id[7] >> 4) & 0b111, 1)
        self.assertEqual(raw_originating_id[7] & 0b111, 1)
        source_id = struct.unpack("!H", raw_originating_id[8:10])[0]
        self.assertEqual(source_id, 1)
        seq_num = struct.unpack("!H", raw_originating_id[10:12])[0]
        self.assertEqual(seq_num, 5)

    def test_originating_transaction_id_unpack(self):
        originating_id = self.originating_transaction_id_msg.get_originating_transaction_id()
        self.assertEqual(self.originating_transaction_id, originating_id)
        id_raw = self.originating_transaction_id_msg.pack()
        generic_reserved_msg = MessageToUserTlv.unpack(id_raw).to_reserved_msg_tlv()
        self.assertIsNotNone(generic_reserved_msg)
        id_2 = generic_reserved_msg.get_originating_transaction_id()
        self.assertEqual(id_2, self.originating_transaction_id)

    def test_put_reponse_state(self):
        self.assertFalse(self.proxy_put_response.is_originating_transaction_id())
        self.assertTrue(self.proxy_put_response.is_cfdp_proxy_operation())
        self.assertFalse(self.proxy_put_response.is_directory_operation())
        self.assertEqual(
            self.proxy_put_response.get_cfdp_proxy_message_type(),
            ProxyMessageType.PUT_RESPONSE,
        )

    def test_put_reponse_pack(self):
        put_response_raw = self.proxy_put_response.pack()
        self._generic_raw_data_verification(put_response_raw, 1, ProxyMessageType.PUT_RESPONSE)
        self.assertEqual((put_response_raw[7] >> 4) & 0b1111, ConditionCode.NO_ERROR)
        self.assertEqual((put_response_raw[7] >> 2) & 0b1, DeliveryCode.DATA_COMPLETE)
        self.assertEqual(put_response_raw[7] & 0b11, FileStatus.FILE_RETAINED)

    def test_put_reponse_unpack(self):
        put_reponse_params = self.proxy_put_response.get_proxy_put_response_params()
        self.assertEqual(put_reponse_params, self.proxy_put_response_params)
        put_response_raw = self.proxy_put_response.pack()
        generic_reserved_msg = MessageToUserTlv.unpack(put_response_raw).to_reserved_msg_tlv()
        self.assertIsNotNone(generic_reserved_msg)
        put_reponse_params_2 = self.proxy_put_response.get_proxy_put_response_params()
        self.assertEqual(put_reponse_params_2, self.proxy_put_response_params)

    def test_proxy_closure_requested_state(self):
        self.assertFalse(self.proxy_closure_requested.is_originating_transaction_id())
        self.assertFalse(self.proxy_closure_requested.is_directory_operation())
        self.assertTrue(self.proxy_closure_requested.is_cfdp_proxy_operation())
        self.assertEqual(
            self.proxy_closure_requested.get_cfdp_proxy_message_type(),
            ProxyMessageType.CLOSURE_REQUEST,
        )

    def test_proxy_closure_requested_pack(self):
        proxy_closure_raw = self.proxy_closure_requested.pack()
        self._generic_raw_data_verification(proxy_closure_raw, 1, ProxyMessageType.CLOSURE_REQUEST)
        self.assertTrue(proxy_closure_raw[7] & 0b1)

    def test_proxy_closure_requested_unpack(self):
        closure_requested = self.proxy_closure_requested.get_proxy_closure_requested()
        self.assertTrue(closure_requested)
        proxy_closure_raw = self.proxy_closure_requested.pack()
        generic_reserved_msg = MessageToUserTlv.unpack(proxy_closure_raw).to_reserved_msg_tlv()
        self.assertTrue(generic_reserved_msg.get_proxy_closure_requested())

    def test_proxy_transmission_mode_state(self):
        self.assertFalse(self.proxy_transmission_mode.is_originating_transaction_id())
        self.assertFalse(self.proxy_transmission_mode.is_directory_operation())
        self.assertTrue(self.proxy_transmission_mode.is_cfdp_proxy_operation())
        self.assertEqual(
            self.proxy_transmission_mode.get_cfdp_proxy_message_type(),
            ProxyMessageType.TRANSMISSION_MODE,
        )

    def test_proxy_transmission_mode_pack(self):
        proxy_transmission_mode_raw = self.proxy_transmission_mode.pack()
        self._generic_raw_data_verification(
            proxy_transmission_mode_raw, 1, ProxyMessageType.TRANSMISSION_MODE
        )
        self.assertEqual(proxy_transmission_mode_raw[7] & 0b1, TransmissionMode.UNACKNOWLEDGED)

    def test_proxy_transmission_mode_unpack(self):
        transmission_mode = self.proxy_transmission_mode.get_proxy_transmission_mode()
        self.assertEqual(transmission_mode, TransmissionMode.UNACKNOWLEDGED)
        transmission_mode_raw = self.proxy_transmission_mode.pack()
        generic_reserved_msg = MessageToUserTlv.unpack(transmission_mode_raw).to_reserved_msg_tlv()
        self.assertEqual(
            generic_reserved_msg.get_proxy_transmission_mode(),
            TransmissionMode.UNACKNOWLEDGED,
        )

    def test_dir_listing_req_state(self):
        self.assertFalse(self.dir_listing_req.is_originating_transaction_id())
        self.assertFalse(self.dir_listing_req.is_cfdp_proxy_operation())
        self.assertTrue(self.dir_listing_req.is_directory_operation())
        self.assertEqual(
            self.dir_listing_req.get_directory_operation_type(),
            DirectoryOperationMessageType.LISTING_REQUEST,
        )

    def test_dir_listing_req_pack(self):
        dir_listing_req_raw = self.dir_listing_req.pack()
        self._generic_raw_data_verification(
            dir_listing_req_raw,
            self.dir_path_lv.packet_len + self.dir_listing_name_lv.packet_len,
            DirectoryOperationMessageType.LISTING_REQUEST,
        )
        dir_path_lv = CfdpLv.unpack(dir_listing_req_raw[7:])
        dir_listing_name_lv = CfdpLv.unpack(dir_listing_req_raw[7 + dir_path_lv.packet_len :])
        self.assertEqual(dir_path_lv, self.dir_path_lv)
        self.assertEqual(dir_listing_name_lv, self.dir_listing_name_lv)

    def test_dir_listing_req_unpack(self):
        dir_listing_req_params = self.dir_listing_req.get_dir_listing_request_params()
        self.assertEqual(dir_listing_req_params, self.dir_params)
        dir_listing_raw = self.dir_listing_req.pack()
        generic_reserved_msg = MessageToUserTlv.unpack(dir_listing_raw).to_reserved_msg_tlv()
        self.assertEqual(
            generic_reserved_msg.get_dir_listing_request_params(),
            self.dir_params,
        )

    def test_dir_listing_response_state(self):
        self.assertFalse(self.dir_listing_response.is_originating_transaction_id())
        self.assertFalse(self.dir_listing_response.is_cfdp_proxy_operation())
        self.assertTrue(self.dir_listing_response.is_directory_operation())
        self.assertEqual(
            self.dir_listing_response.get_directory_operation_type(),
            DirectoryOperationMessageType.LISTING_RESPONSE,
        )

    def test_dir_listing_response_pack(self):
        dir_listing_response_raw = self.dir_listing_response.pack()
        self._generic_raw_data_verification(
            dir_listing_response_raw,
            1 + self.dir_path_lv.packet_len + self.dir_listing_name_lv.packet_len,
            DirectoryOperationMessageType.LISTING_RESPONSE,
        )
        success_response = (dir_listing_response_raw[7] >> 7) & 0b1
        dir_path_lv = CfdpLv.unpack(dir_listing_response_raw[8:])
        dir_listing_name_lv = CfdpLv.unpack(dir_listing_response_raw[8 + dir_path_lv.packet_len :])
        self.assertTrue(success_response)
        self.assertEqual(self.dir_path_lv, dir_path_lv)
        self.assertEqual(self.dir_listing_name_lv, dir_listing_name_lv)

    def test_dir_listing_response_unpack(self):
        dir_listing_response_params = self.dir_listing_req.get_dir_listing_request_params()
        self.assertEqual(dir_listing_response_params, self.dir_params)
        dir_listing_raw = self.dir_listing_response.pack()
        generic_reserved_msg = MessageToUserTlv.unpack(dir_listing_raw).to_reserved_msg_tlv()
        (
            success_response,
            dir_listing_params,
        ) = generic_reserved_msg.get_dir_listing_response_params()
        self.assertTrue(success_response)
        self.assertEqual(dir_listing_params, self.dir_params)

    def test_dir_listing_options_state(self):
        self.assertFalse(self.dir_listing_options_msg.is_originating_transaction_id())
        self.assertFalse(self.dir_listing_options_msg.is_cfdp_proxy_operation())
        self.assertTrue(self.dir_listing_options_msg.is_directory_operation())
        self.assertEqual(
            self.dir_listing_options_msg.get_directory_operation_type(),
            DirectoryOperationMessageType.CUSTOM_LISTING_PARAMETERS,
        )

    def test_dir_listing_options_pack(self):
        dir_listing_req_params_raw = self.dir_listing_options_msg.pack()
        self._generic_raw_data_verification(
            dir_listing_req_params_raw,
            1,
            DirectoryOperationMessageType.CUSTOM_LISTING_PARAMETERS,
        )
        self.assertTrue((dir_listing_req_params_raw[7] >> 1) & 0b1)
        self.assertTrue(dir_listing_req_params_raw[7] & 0b1)

    def test_dir_listing_options_unpack(self):
        dir_listing_options = self.dir_listing_options_msg.get_dir_listing_options()
        self.assertEqual(dir_listing_options, self.dir_listing_options)
        dir_listing_opt_raw = self.dir_listing_options_msg.pack()
        generic_reserved_msg = MessageToUserTlv.unpack(dir_listing_opt_raw).to_reserved_msg_tlv()
        listing_opts_from_raw = generic_reserved_msg.get_dir_listing_options()
        self.assertEqual(listing_opts_from_raw, self.dir_listing_options)

    def test_proxy_cancel_request_state(self):
        self.assertFalse(self.proxy_cancel_request.is_originating_transaction_id())
        self.assertFalse(self.proxy_cancel_request.is_directory_operation())
        self.assertTrue(self.proxy_cancel_request.is_cfdp_proxy_operation())
        self.assertEqual(
            self.proxy_cancel_request.get_cfdp_proxy_message_type(),
            ProxyMessageType.PUT_CANCEL,
        )

    def test_proxy_cancel_request_pack(self):
        proxy_put_cancel_raw = self.proxy_cancel_request.pack()
        self._generic_raw_data_verification(proxy_put_cancel_raw, 0, ProxyMessageType.PUT_CANCEL)

    def test_proxy_cancel_request_unpack(self):
        proxy_put_cancel_raw = self.proxy_cancel_request.pack()
        generic_reserved_msg = MessageToUserTlv.unpack(proxy_put_cancel_raw).to_reserved_msg_tlv()
        self.assertEqual(
            generic_reserved_msg.get_cfdp_proxy_message_type(),
            ProxyMessageType.PUT_CANCEL,
        )

    def test_proxy_put_response_params_from_finished_params(self):
        finished_params = FinishedParams(
            ConditionCode.NO_ERROR, DeliveryCode.DATA_COMPLETE, FileStatus.FILE_RETAINED
        )
        self.proxy_put_response_params = ProxyPutResponseParams.from_finished_params(
            finished_params
        )
        self.assertEqual(
            self.proxy_put_response_params.condition_code,
            finished_params.condition_code,
        )
        self.assertEqual(
            self.proxy_put_response_params.delivery_code, finished_params.delivery_code
        )
        self.assertEqual(self.proxy_put_response_params.file_status, finished_params.file_status)

    def test_proxy_put_req_param_api(self):
        src_as_str = "/tmp/test.txt"
        dest_as_str = "/tmp/test2.txt"
        proxy_put_req_param_api = ProxyPutRequestParams(
            ByteFieldU16(5),
            CfdpLv.from_str(src_as_str),
            CfdpLv.from_str(dest_as_str),
        )
        self.assertEqual(proxy_put_req_param_api.source_file_as_str, src_as_str)
        self.assertEqual(proxy_put_req_param_api.dest_file_as_str, dest_as_str)
        self.assertEqual(proxy_put_req_param_api.source_file_as_path, Path(src_as_str))
        self.assertEqual(proxy_put_req_param_api.dest_file_as_path, Path(dest_as_str))
