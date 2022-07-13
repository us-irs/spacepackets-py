from unittest import TestCase

from spacepackets.cfdp import (
    FileStoreResponseTlv,
    FilestoreActionCode,
    FilestoreResponseStatusCode,
    TlvHolder,
    TlvTypes,
    TlvTypeMissmatch,
)


class TestFsResponseTlv(TestCase):
    def test_fs_response_tlv(self):
        fs_response_tlv = FileStoreResponseTlv(
            action_code=FilestoreActionCode.APPEND_FILE_SNP,
            first_file_name="test.txt",
            status_code=FilestoreResponseStatusCode.APPEND_NOT_PERFORMED,
        )
        fs_response_tlv.generate_tlv()
        fs_response_tlv_tlv = fs_response_tlv.tlv
        wrapper = TlvHolder(fs_response_tlv)
        fs_reply_tlv_from_fac = wrapper.to_fs_response()

        self.assertEqual(fs_reply_tlv_from_fac.pack(), fs_response_tlv.pack())
        fs_response_tlv_tlv.tlv_type = TlvTypes.ENTITY_ID
        with self.assertRaises(TlvTypeMissmatch):
            FileStoreResponseTlv.from_tlv(cfdp_tlv=fs_response_tlv_tlv)
        fs_response_tlv_tlv.tlv_type = TlvTypes.FILESTORE_RESPONSE
        fs_response_tlv_raw = fs_response_tlv.pack()
        # This status code does not exist for the Create file action code 0b0000
        fs_response_tlv_raw[2] = 0b00001000
        with self.assertRaises(ValueError):
            FileStoreResponseTlv.unpack(raw_bytes=fs_response_tlv_raw)
        # Wrong ID
        fs_response_tlv_raw[0] = TlvTypes.ENTITY_ID
        with self.assertRaises(TlvTypeMissmatch):
            FileStoreResponseTlv.unpack(raw_bytes=fs_response_tlv_raw)
        fs_response_tlv_raw[0] = TlvTypes.FILESTORE_RESPONSE
        fs_response_tlv_raw[2] = 0b11110000
        with self.assertRaises(ValueError):
            FileStoreResponseTlv.unpack(raw_bytes=fs_response_tlv_raw)
