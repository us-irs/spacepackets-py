from unittest import TestCase

from spacepackets.cfdp.lv import CfdpLv
from spacepackets.cfdp.tlv import CfdpTlv, TlvTypes, map_enum_status_code_to_action_status_code, \
    FilestoreResponseStatusCode, FilestoreActionCode, map_int_status_code_to_enum, \
    EntityIdTlv, FlowLabelTlv, FileStoreRequestTlv, FileStoreResponseTlv, MessageToUserTlv, \
    FaultHandlerOverrideTlv, concrete_tlv_factory, ConditionCode, \
    FaultHandlerOverrideHandlerCodes, create_cfdp_proxy_and_dir_op_message_marker


class TestTlvsLvs(TestCase):
    def test_tlvs(self):
        test_tlv = CfdpTlv(
            tlv_type=TlvTypes.FILESTORE_REQUEST,
            value=bytes([0, 1, 2, 3, 4])
        )
        self.assertEqual(test_tlv.tlv_type, TlvTypes.FILESTORE_REQUEST)
        self.assertEqual(test_tlv.length, 5)
        self.assertEqual(test_tlv.value, bytes([0, 1, 2, 3, 4]))
        self.assertEqual(test_tlv.packet_len, 7)

        test_tlv_package = test_tlv.pack()
        test_tlv_unpacked = CfdpTlv.unpack(raw_bytes=test_tlv_package)
        self.assertEqual(test_tlv_unpacked.tlv_type, TlvTypes.FILESTORE_REQUEST)
        self.assertEqual(test_tlv_unpacked.length, 5)
        self.assertEqual(test_tlv_unpacked.value, bytes([0, 1, 2, 3, 4]))

        # Length field missmatch
        another_tlv = bytes([TlvTypes.ENTITY_ID, 1, 3, 4])
        another_tlv_unpacked = CfdpTlv.unpack(raw_bytes=another_tlv)
        self.assertEqual(another_tlv_unpacked.value, bytes([3]))
        self.assertEqual(another_tlv_unpacked.length, 1)

        faulty_tlv = bytes([TlvTypes.FILESTORE_REQUEST, 200, 2, 3])
        self.assertRaises(ValueError, CfdpTlv.unpack, faulty_tlv)
        # Too much too pack
        faulty_values = bytes(300)
        self.assertRaises(ValueError, CfdpTlv, TlvTypes.FILESTORE_REQUEST, faulty_values)
        # Too short to unpack
        faulty_tlv = bytes([0])
        self.assertRaises(ValueError, CfdpTlv.unpack, faulty_tlv)
        # Invalid type when unpacking
        faulty_tlv = bytes([TlvTypes.ENTITY_ID + 3, 2, 1, 2])
        self.assertRaises(ValueError, CfdpTlv.unpack, faulty_tlv)

        action_code, status_code = map_enum_status_code_to_action_status_code(
            FilestoreResponseStatusCode.APPEND_NOT_PERFORMED
        )
        self.assertEqual(action_code, FilestoreActionCode.APPEND_FILE_SNP)
        self.assertEqual(status_code, 0b1111)
        action_code, status_code = map_enum_status_code_to_action_status_code(
            FilestoreResponseStatusCode.INVALID
        )
        self.assertEqual(action_code, -1)
        status_code = map_int_status_code_to_enum(
            action_code=FilestoreActionCode.APPEND_FILE_SNP, status_code=0b1111
        )
        self.assertEqual(status_code, FilestoreResponseStatusCode.APPEND_NOT_PERFORMED)
        invalid_code = map_int_status_code_to_enum(
            action_code=FilestoreActionCode.APPEND_FILE_SNP, status_code=0b1100
        )
        self.assertEqual(invalid_code, FilestoreResponseStatusCode.INVALID)

    def test_lvs(self):
        test_values = bytes([0, 1, 2])
        test_lv = CfdpLv(
            value=test_values
        )
        self.assertEqual(test_lv.value, test_values)
        self.assertEqual(test_lv.len, 3)
        self.assertEqual(test_lv.packet_len, 4)
        test_lv_packed = test_lv.pack()
        self.assertEqual(len(test_lv_packed), 4)
        self.assertEqual(test_lv_packed[0], 3)
        self.assertEqual(test_lv_packed[1: 1 + 3], test_values)

        CfdpLv.unpack(raw_bytes=test_lv_packed)
        self.assertEqual(test_lv.value, test_values)
        self.assertEqual(test_lv.len, 3)
        self.assertEqual(test_lv.packet_len, 4)

        # Too much too pack
        faulty_values = bytearray(300)
        self.assertRaises(ValueError, CfdpLv, faulty_values)
        # Too large to unpack
        faulty_values[0] = 20
        self.assertRaises(ValueError, CfdpLv.unpack, faulty_values[0:15])
        # Too short to unpack
        faulty_lv = bytes([0])
        self.assertRaises(ValueError, CfdpTlv.unpack, faulty_lv)

    def test_entity_id_tlv(self):
        entity_id_tlv = EntityIdTlv(
            entity_id=bytes([0x00, 0x01, 0x02, 0x03])
        )
        entity_id_tlv_tlv = entity_id_tlv.tlv
        entity_id_tlv_from_factory = concrete_tlv_factory(
            cfdp_tlv=entity_id_tlv_tlv, _tlv_type=EntityIdTlv
        )
        self.assertEqual(entity_id_tlv_from_factory.pack(), entity_id_tlv.pack())
        entity_id_tlv_tlv.tlv_type = TlvTypes.FILESTORE_REQUEST
        with self.assertRaises(ValueError):
            EntityIdTlv.from_tlv(cfdp_tlv=entity_id_tlv_tlv)

    def test_fs_req_tlv(self):
        fs_reqeust_tlv = FileStoreRequestTlv(
            action_code=FilestoreActionCode.APPEND_FILE_SNP,
            first_file_name='test.txt'
        )
        fs_reqeust_tlv_tlv = fs_reqeust_tlv.tlv
        fs_req_tlv_from_fac = concrete_tlv_factory(
            cfdp_tlv=fs_reqeust_tlv_tlv, _tlv_type=FileStoreRequestTlv
        )
        self.assertEqual(fs_req_tlv_from_fac.pack(), fs_reqeust_tlv.pack())
        fs_reqeust_tlv_raw = fs_reqeust_tlv.pack()
        fs_reqeust_tlv_unpacked = FileStoreRequestTlv.unpack(raw_bytes=fs_reqeust_tlv_raw)
        self.assertEqual(fs_reqeust_tlv_unpacked.first_file_name, 'test.txt')
        self.assertEqual(fs_reqeust_tlv_unpacked.action_code, FilestoreActionCode.APPEND_FILE_SNP)

        fs_reqeust_tlv_tlv.tlv_type = TlvTypes.ENTITY_ID
        with self.assertRaises(ValueError):
            FileStoreRequestTlv.from_tlv(cfdp_tlv=fs_reqeust_tlv_tlv)

    def test_fs_response_tlv(self):
        fs_response_tlv = FileStoreResponseTlv(
            action_code=FilestoreActionCode.APPEND_FILE_SNP,
            first_file_name='test.txt',
            status_code=FilestoreResponseStatusCode.APPEND_NOT_PERFORMED
        )
        fs_response_tlv_tlv = fs_response_tlv.tlv
        fs_reply_tlv_from_fac = concrete_tlv_factory(
            cfdp_tlv=fs_response_tlv_tlv, _tlv_type=FileStoreResponseTlv
        )

        self.assertEqual(fs_reply_tlv_from_fac.pack(), fs_response_tlv.pack())
        fs_response_tlv_tlv.tlv_type = TlvTypes.ENTITY_ID
        with self.assertRaises(ValueError):
            FileStoreResponseTlv.from_tlv(cfdp_tlv=fs_response_tlv_tlv)
        fs_response_tlv_tlv.tlv_type = TlvTypes.FILESTORE_RESPONSE
        fs_response_tlv_raw = fs_response_tlv.pack()
        # This status code does not exist for the Create file action code 0b0000
        fs_response_tlv_raw[2] = 0b00001000
        with self.assertRaises(ValueError):
            FileStoreResponseTlv.unpack(raw_bytes=fs_response_tlv_raw)
        # Wrong ID
        fs_response_tlv_raw[0] = TlvTypes.ENTITY_ID
        with self.assertRaises(ValueError):
            FileStoreResponseTlv.unpack(raw_bytes=fs_response_tlv_raw)
        fs_response_tlv_raw[0] = TlvTypes.FILESTORE_RESPONSE
        fs_response_tlv_raw[2] = 0b11110000
        with self.assertRaises(ValueError):
            FileStoreResponseTlv.unpack(raw_bytes=fs_response_tlv_raw)

    def test_fault_handler_override_tlv(self):
        fault_handler_ovvrd_tlv = FaultHandlerOverrideTlv(
            condition_code=ConditionCode.POSITIVE_ACK_LIMIT_REACHED,
            handler_code=FaultHandlerOverrideHandlerCodes.IGNORE_ERROR
        )
        fault_handler_ovvrd_tlv_tlv = fault_handler_ovvrd_tlv.tlv
        fault_handler_ovvrd_tlv_from_fac = concrete_tlv_factory(
            cfdp_tlv=fault_handler_ovvrd_tlv_tlv, _tlv_type=FaultHandlerOverrideTlv
        )
        self.assertEqual(fault_handler_ovvrd_tlv_from_fac.pack(), fault_handler_ovvrd_tlv.pack())
        fault_handler_ovvrd_tlv_tlv.tlv_type = TlvTypes.ENTITY_ID
        with self.assertRaises(ValueError):
            FaultHandlerOverrideTlv.from_tlv(cfdp_tlv=fault_handler_ovvrd_tlv_tlv)

    def test_msg_to_user_tlv(self):
        msg_to_usr_tlv = MessageToUserTlv(
            value=bytes([0x00])
        )
        msg_to_usr_tlv_tlv = msg_to_usr_tlv.tlv
        msg_to_usr_tlv_from_fac = concrete_tlv_factory(
            cfdp_tlv=msg_to_usr_tlv_tlv, _tlv_type=MessageToUserTlv
        )
        self.assertEqual(msg_to_usr_tlv_from_fac.pack(), msg_to_usr_tlv.pack())
        msg_to_usr_tlv_tlv.tlv_type = TlvTypes.FILESTORE_REQUEST
        with self.assertRaises(ValueError):
            MessageToUserTlv.from_tlv(cfdp_tlv=msg_to_usr_tlv_tlv)
        msg_to_usr_tlv_tlv.tlv_type = TlvTypes.MESSAGE_TO_USER
        msg_to_usr_tlv_raw = msg_to_usr_tlv.pack()
        msg_to_usr_tlv_unpacked = MessageToUserTlv.unpack(raw_bytes=msg_to_usr_tlv_raw)
        self.assertEqual(msg_to_usr_tlv_unpacked.tlv.value, bytes([0x00]))
        self.assertFalse(msg_to_usr_tlv_unpacked.is_standard_proxy_dir_ops_msg())
        proxy_val = create_cfdp_proxy_and_dir_op_message_marker()
        msg_to_usr_tlv = MessageToUserTlv(
            value=proxy_val
        )
        self.assertTrue(msg_to_usr_tlv.is_standard_proxy_dir_ops_msg())

    def test_flow_label_tlv(self):
        flow_label_tlv = FlowLabelTlv(
            value=bytes([0x00])
        )
        flow_label_tlv_tlv = flow_label_tlv.tlv
        flow_label_tlv_from_fac = concrete_tlv_factory(
            cfdp_tlv=flow_label_tlv_tlv, _tlv_type=FlowLabelTlv
        )
        self.assertEqual(flow_label_tlv_from_fac.pack(), flow_label_tlv.pack())
        flow_label_tlv_raw = flow_label_tlv.pack()
        flow_label_tlv_unpacked = FlowLabelTlv.unpack(raw_bytes=flow_label_tlv_raw)
        self.assertEqual(flow_label_tlv_unpacked.tlv.value, bytes([0x00]))
        flow_label_tlv_tlv.tlv_type = TlvTypes.FILESTORE_REQUEST
        with self.assertRaises(ValueError):
            FlowLabelTlv.from_tlv(cfdp_tlv=flow_label_tlv_tlv)
        flow_label_tlv_raw[0] = TlvTypes.FILESTORE_REQUEST
        with self.assertRaises(ValueError):
            FlowLabelTlv.unpack(raw_bytes=flow_label_tlv_raw)
