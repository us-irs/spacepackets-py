from unittest import TestCase

from spacepackets.cfdp import TlvTypes, CfdpTlv
from spacepackets.cfdp.tlv import (
    map_enum_status_code_to_action_status_code,
    FilestoreResponseStatusCode,
    FilestoreActionCode,
    map_int_status_code_to_enum,
)


class TestTlvs(TestCase):
    def test_basic(self):
        test_tlv = CfdpTlv(
            tlv_type=TlvTypes.FILESTORE_REQUEST, value=bytes([0, 1, 2, 3, 4])
        )
        self.assertEqual(test_tlv.tlv_type, TlvTypes.FILESTORE_REQUEST)
        self.assertEqual(test_tlv.length, 5)
        self.assertEqual(test_tlv.value, bytes([0, 1, 2, 3, 4]))
        self.assertEqual(test_tlv.packet_len, 7)

    def test_packing(self):
        test_tlv = CfdpTlv(
            tlv_type=TlvTypes.FILESTORE_REQUEST, value=bytes([0, 1, 2, 3, 4])
        )
        test_tlv_package = test_tlv.pack()
        test_tlv_unpacked = CfdpTlv.unpack(data=test_tlv_package)
        self.assertEqual(test_tlv_unpacked.tlv_type, TlvTypes.FILESTORE_REQUEST)
        self.assertEqual(test_tlv_unpacked.length, 5)
        self.assertEqual(test_tlv_unpacked.value, bytes([0, 1, 2, 3, 4]))

    def test_length_field_missmatch(self):
        another_tlv = bytes([TlvTypes.ENTITY_ID, 1, 3, 4])
        another_tlv_unpacked = CfdpTlv.unpack(data=another_tlv)
        self.assertEqual(another_tlv_unpacked.value, bytes([3]))
        self.assertEqual(another_tlv_unpacked.length, 1)

        faulty_tlv = bytes([TlvTypes.FILESTORE_REQUEST, 200, 2, 3])
        self.assertRaises(ValueError, CfdpTlv.unpack, faulty_tlv)

    def test_too_much_to_pack(self):
        faulty_values = bytes(300)
        self.assertRaises(
            ValueError, CfdpTlv, TlvTypes.FILESTORE_REQUEST, faulty_values
        )

    def test_too_short_to_unpack(self):
        # Too short to unpack
        faulty_tlv = bytes([0])
        self.assertRaises(ValueError, CfdpTlv.unpack, faulty_tlv)

    def test_invalid_type(self):
        # Invalid type when unpacking
        faulty_tlv = bytes([TlvTypes.ENTITY_ID + 3, 2, 1, 2])
        self.assertRaises(ValueError, CfdpTlv.unpack, faulty_tlv)

    def test_status_code_converters(self):
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

    def test_tlv_print(self):
        test_tlv = CfdpTlv(
            tlv_type=TlvTypes.FILESTORE_REQUEST, value=bytes([0, 1, 2, 3, 4])
        )
        print(test_tlv)
        print(f"{test_tlv!r}")
