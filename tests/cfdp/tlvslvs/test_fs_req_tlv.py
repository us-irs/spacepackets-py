from unittest import TestCase

from spacepackets.cfdp import (
    FileStoreRequestTlv,
    FilestoreActionCode,
    TlvHolder,
    TlvTypeMissmatch,
    TlvTypes,
    CfdpTlv,
)


class TestFsReqTlv(TestCase):
    def setUp(self) -> None:
        self.fs_reqeust_tlv = FileStoreRequestTlv(
            action_code=FilestoreActionCode.APPEND_FILE_SNP, first_file_name="test.txt"
        )
        self.cfdp_tlv = CfdpTlv(
            tlv_type=TlvTypes.FILESTORE_REQUEST, value=self.fs_reqeust_tlv.value
        )

    def test_basic(self):
        self.assertEqual(self.fs_reqeust_tlv.tlv_type, TlvTypes.FILESTORE_REQUEST)
        self.assertEqual(
            self.fs_reqeust_tlv.action_code, FilestoreActionCode.APPEND_FILE_SNP
        )
        # 2 bytes header, action code byte, 9 bytes first file name,
        # 1 byte second file name empty TLV
        self.assertEqual(self.fs_reqeust_tlv.packet_len, 13)

    def test_holder(self):
        self.fs_reqeust_tlv.generate_tlv()
        holder = TlvHolder(self.fs_reqeust_tlv)
        fs_req_tlv_from_fac = holder.to_fs_request()
        self.assertEqual(fs_req_tlv_from_fac, self.fs_reqeust_tlv)

    def test_holder_cfdp_tlv(self):
        holder = TlvHolder(self.cfdp_tlv)
        fs_req_tlv = holder.to_fs_request()
        self.assertEqual(fs_req_tlv, self.fs_reqeust_tlv)

    def test_from_cfdp_tlv(self):
        self.assertEqual(
            FileStoreRequestTlv.from_tlv(self.cfdp_tlv), self.fs_reqeust_tlv
        )

    def test_fs_req_tlv(self):
        self.fs_reqeust_tlv.generate_tlv()
        fs_reqeust_tlv_tlv = self.fs_reqeust_tlv.tlv
        fs_reqeust_tlv_raw = self.fs_reqeust_tlv.pack()
        fs_reqeust_tlv_unpacked = FileStoreRequestTlv.unpack(data=fs_reqeust_tlv_raw)
        self.assertEqual(fs_reqeust_tlv_unpacked.first_file_name, "test.txt")
        self.assertEqual(
            fs_reqeust_tlv_unpacked.action_code, FilestoreActionCode.APPEND_FILE_SNP
        )
        fs_reqeust_tlv_tlv.tlv_type = TlvTypes.ENTITY_ID
        with self.assertRaises(TlvTypeMissmatch):
            FileStoreRequestTlv.from_tlv(cfdp_tlv=fs_reqeust_tlv_tlv)
