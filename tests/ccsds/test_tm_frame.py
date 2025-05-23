from unittest import TestCase

from spacepackets.ccsds.tm_frame import (
    MasterChannelId,
    TmFramePrimaryHeader,
    TmTransferFrame,
    TransferFrameDataFieldStatus,
    TransferFrameSecondaryHeader,
)
from spacepackets.exceptions import BytesTooShortError, InvalidCrcCcitt16Error

MCI = MasterChannelId(transfer_frame_version=3, spacecraft_id=520)
DFS = TransferFrameDataFieldStatus(
    secondary_header_flag=True,
    sync_flag=True,
    packet_order_flag=True,
    segment_len_id=1,
    first_header_pointer=2046,
)


class TestTmFrame(TestCase):
    def setUp(self):
        self.tm_primary_header = TmFramePrimaryHeader(
            master_channel_id=MCI,
            vc_id=5,
            ocf_flag=False,
            master_ch_frame_count=10,
            vc_frame_count=0,
            frame_datafield_status=DFS,
        )

    def test_tm_frame_primary_header_init(self):
        self.assertEqual(self.tm_primary_header.master_channel_id, MCI)
        self.assertEqual(self.tm_primary_header.vc_id, 5)
        self.assertEqual(self.tm_primary_header.ocf_flag, False)
        self.assertEqual(self.tm_primary_header.master_ch_frame_count, 10)
        self.assertEqual(self.tm_primary_header.vc_frame_count, 0)
        self.assertEqual(self.tm_primary_header.frame_datafield_status, DFS)

    def test_pack_unpack_transfer_data_field_status(self):
        packed = TransferFrameDataFieldStatus.pack(DFS)
        unpacked = TransferFrameDataFieldStatus.unpack(packed)
        self.assertEqual(DFS, unpacked)

    def test_unpack_data_field_status_too_short(self):
        self.assertRaises(BytesTooShortError, TransferFrameDataFieldStatus.unpack, b"")

    def test_pack_unpack_primary_header(self):
        prim_header = TmFramePrimaryHeader(MCI, 6, True, 7, 8, DFS)
        packed = TmFramePrimaryHeader.pack(prim_header)
        unpacked = TmFramePrimaryHeader.unpack(packed)
        self.assertEqual(prim_header.master_channel_id, unpacked.master_channel_id)
        self.assertEqual(prim_header.vc_id, unpacked.vc_id)
        self.assertEqual(prim_header.ocf_flag, unpacked.ocf_flag)
        self.assertEqual(prim_header.master_ch_frame_count, unpacked.master_ch_frame_count)
        self.assertEqual(prim_header.vc_frame_count, unpacked.vc_frame_count)
        self.assertEqual(prim_header.frame_datafield_status, unpacked.frame_datafield_status)

    def test_pack_unpack_secondary_header(self):
        secondary_header = TransferFrameSecondaryHeader(0, 1, b"\x02")
        packed = TransferFrameSecondaryHeader.pack(secondary_header)
        unpacked = TransferFrameSecondaryHeader.unpack(packed)
        self.assertEqual(secondary_header, unpacked)

    def test_pack_secondary_header_data_too_long(self):
        secondary_header = TransferFrameSecondaryHeader(0, 64, b"\x02")  # max 63
        self.assertRaises(ValueError, TransferFrameSecondaryHeader.pack, secondary_header)

    def test_unpack_secondary_header_too_short(self):
        self.assertRaises(BytesTooShortError, TransferFrameSecondaryHeader.unpack, b"")

    def test_unpack_transfer_frame_fefc_too_short_ocf(self):
        packed = b"\x00?\x00\x00\x1f\xfe\x00\x00\x01\x02\x01\x00\x00\x00\x81"
        self.assertRaises(BytesTooShortError, TmTransferFrame.unpack, packed, 16, True)

    def test_unpack_transfer_frame_fefc_too_short_no_ocf(self):
        packed = b"\x00>\x00\x00\x1f\xfe\x00\x01\x02\x8f"
        self.assertRaises(BytesTooShortError, TmTransferFrame.unpack, packed, 11, True)

    def test_unpack_transfer_frame_invalid_fefc(self):
        packed = (
            b"\x00?\x00\x00\x1f\xfe\x00\x00\x01\x02\x01\x00\x00\x00\x01\x23"  # actual is \x81\x4a
        )
        self.assertRaises(InvalidCrcCcitt16Error, TmTransferFrame.unpack, packed, 16, True)

    def test_unpack_transfer_frame_ocf_too_short(self):
        packed = b"\x00?\x00\x00\x1f\xfe\x00\x01\x02\x10\x00\x00"
        self.assertRaises(BytesTooShortError, TmTransferFrame.unpack, packed, 13, True)

    def test_pack_unpack_transfer_frame_sec_header_ocf_fefc(self):
        mci = MasterChannelId(transfer_frame_version=0, spacecraft_id=3)
        dfs = TransferFrameDataFieldStatus(
            secondary_header_flag=True,
            sync_flag=False,
            packet_order_flag=False,
            segment_len_id=3,
            first_header_pointer=2046,
        )
        primary_header = TmFramePrimaryHeader(
            master_channel_id=mci,
            vc_id=7,
            ocf_flag=True,
            master_ch_frame_count=0,
            vc_frame_count=0,
            frame_datafield_status=dfs,
        )
        secondary_header = TransferFrameSecondaryHeader(0, 1, b"\x05")
        tm_frame = TmTransferFrame(
            17,
            primary_header,
            secondary_header,
            b"\x00\x01\x02",
            b"\x10\x00\x00\x00",
            b"\x62\x6a",
        )
        packed = tm_frame.pack()
        unpacked = tm_frame.unpack(packed, 17, True)
        self.assertEqual(tm_frame.data_field, unpacked.data_field)
        self.assertEqual(tm_frame.op_ctrl_field, unpacked.op_ctrl_field)
        self.assertEqual(tm_frame.frame_error_control, unpacked.frame_error_control)

    def test_pack_unpack_transfer_frame_sec_header_no_ocf_fefc(self):
        mci = MasterChannelId(transfer_frame_version=0, spacecraft_id=3)
        dfs = TransferFrameDataFieldStatus(
            secondary_header_flag=True,
            sync_flag=False,
            packet_order_flag=False,
            segment_len_id=3,
            first_header_pointer=2046,
        )
        primary_header = TmFramePrimaryHeader(
            master_channel_id=mci,
            vc_id=7,
            ocf_flag=False,
            master_ch_frame_count=0,
            vc_frame_count=0,
            frame_datafield_status=dfs,
        )
        secondary_header = TransferFrameSecondaryHeader(0, 1, b"\x05")
        tm_frame = TmTransferFrame(
            13, primary_header, secondary_header, b"\x00\x01\x02", None, b"\x42\x73"
        )
        packed = tm_frame.pack()
        unpacked = tm_frame.unpack(packed, 13, True)
        self.assertEqual(tm_frame.data_field, unpacked.data_field)
        self.assertEqual(tm_frame.op_ctrl_field, unpacked.op_ctrl_field)
        self.assertEqual(tm_frame.frame_error_control, unpacked.frame_error_control)

    def test_pack_unpack_transfer_frame_sec_header_ocf_no_fefc(self):
        mci = MasterChannelId(transfer_frame_version=0, spacecraft_id=3)
        dfs = TransferFrameDataFieldStatus(
            secondary_header_flag=True,
            sync_flag=False,
            packet_order_flag=False,
            segment_len_id=3,
            first_header_pointer=2046,
        )
        primary_header = TmFramePrimaryHeader(
            master_channel_id=mci,
            vc_id=7,
            ocf_flag=True,
            master_ch_frame_count=0,
            vc_frame_count=0,
            frame_datafield_status=dfs,
        )
        secondary_header = TransferFrameSecondaryHeader(0, 1, b"\x05")
        tm_frame = TmTransferFrame(
            15,
            primary_header,
            secondary_header,
            b"\x00\x01\x02",
            b"\x10\x00\x00\x00",
            None,
        )
        packed = tm_frame.pack()
        unpacked = tm_frame.unpack(packed, 15, False)
        self.assertEqual(tm_frame.data_field, unpacked.data_field)
        self.assertEqual(tm_frame.op_ctrl_field, unpacked.op_ctrl_field)
        self.assertEqual(tm_frame.frame_error_control, unpacked.frame_error_control)

    def test_pack_unpack_transfer_frame_sec_header_no_ocf_no_fefc(self):
        mci = MasterChannelId(transfer_frame_version=0, spacecraft_id=3)
        dfs = TransferFrameDataFieldStatus(
            secondary_header_flag=True,
            sync_flag=False,
            packet_order_flag=False,
            segment_len_id=3,
            first_header_pointer=2046,
        )
        primary_header = TmFramePrimaryHeader(
            master_channel_id=mci,
            vc_id=7,
            ocf_flag=False,
            master_ch_frame_count=0,
            vc_frame_count=0,
            frame_datafield_status=dfs,
        )
        secondary_header = TransferFrameSecondaryHeader(0, 1, b"\x05")
        tm_frame = TmTransferFrame(
            11, primary_header, secondary_header, b"\x00\x01\x02", None, None
        )
        packed = tm_frame.pack()
        unpacked = tm_frame.unpack(packed, 11, False)
        self.assertEqual(tm_frame.data_field, unpacked.data_field)
        self.assertEqual(tm_frame.op_ctrl_field, unpacked.op_ctrl_field)
        self.assertEqual(tm_frame.frame_error_control, unpacked.frame_error_control)

    def test_pack_unpack_transfer_frame_no_sec_header_ocf_fefc(self):
        mci = MasterChannelId(transfer_frame_version=0, spacecraft_id=3)
        dfs = TransferFrameDataFieldStatus(
            secondary_header_flag=False,
            sync_flag=False,
            packet_order_flag=False,
            segment_len_id=3,
            first_header_pointer=2046,
        )
        primary_header = TmFramePrimaryHeader(
            master_channel_id=mci,
            vc_id=7,
            ocf_flag=True,
            master_ch_frame_count=0,
            vc_frame_count=0,
            frame_datafield_status=dfs,
        )
        tm_frame = TmTransferFrame(
            15, primary_header, None, b"\x00\x01\x02", b"\x10\x00\x00\x00", b"\x60\xad"
        )
        packed = tm_frame.pack()
        unpacked = tm_frame.unpack(packed, 15, True)
        self.assertEqual(tm_frame.data_field, unpacked.data_field)
        self.assertEqual(tm_frame.op_ctrl_field, unpacked.op_ctrl_field)
        self.assertEqual(tm_frame.frame_error_control, unpacked.frame_error_control)

    def test_pack_unpack_transfer_frame_no_sec_header_no_ocf_fefc(self):
        mci = MasterChannelId(transfer_frame_version=0, spacecraft_id=3)
        dfs = TransferFrameDataFieldStatus(
            secondary_header_flag=False,
            sync_flag=False,
            packet_order_flag=False,
            segment_len_id=3,
            first_header_pointer=2046,
        )
        primary_header = TmFramePrimaryHeader(
            master_channel_id=mci,
            vc_id=7,
            ocf_flag=False,
            master_ch_frame_count=0,
            vc_frame_count=0,
            frame_datafield_status=dfs,
        )
        tm_frame = TmTransferFrame(11, primary_header, None, b"\x00\x01\x02", None, b"\x8f\x78")
        packed = tm_frame.pack()
        unpacked = tm_frame.unpack(packed, 11, True)
        self.assertEqual(tm_frame.data_field, unpacked.data_field)
        self.assertEqual(tm_frame.op_ctrl_field, unpacked.op_ctrl_field)
        self.assertEqual(tm_frame.frame_error_control, unpacked.frame_error_control)

    def test_pack_unpack_transfer_frame_no_sec_header_ocf_no_fefc(self):
        mci = MasterChannelId(transfer_frame_version=0, spacecraft_id=3)
        dfs = TransferFrameDataFieldStatus(
            secondary_header_flag=False,
            sync_flag=False,
            packet_order_flag=False,
            segment_len_id=3,
            first_header_pointer=2046,
        )
        primary_header = TmFramePrimaryHeader(
            master_channel_id=mci,
            vc_id=7,
            ocf_flag=True,
            master_ch_frame_count=0,
            vc_frame_count=0,
            frame_datafield_status=dfs,
        )
        tm_frame = TmTransferFrame(
            13, primary_header, None, b"\x00\x01\x02", b"\x10\x00\x00\x00", None
        )
        packed = tm_frame.pack()
        unpacked = tm_frame.unpack(packed, 13, False)
        self.assertEqual(tm_frame.data_field, unpacked.data_field)
        self.assertEqual(tm_frame.op_ctrl_field, unpacked.op_ctrl_field)
        self.assertEqual(tm_frame.frame_error_control, unpacked.frame_error_control)

    def test_pack_unpack_transfer_frame_no_sec_header_no_ocf_no_fefc(self):
        mci = MasterChannelId(transfer_frame_version=0, spacecraft_id=3)
        dfs = TransferFrameDataFieldStatus(
            secondary_header_flag=False,
            sync_flag=False,
            packet_order_flag=False,
            segment_len_id=3,
            first_header_pointer=2046,
        )
        primary_header = TmFramePrimaryHeader(
            master_channel_id=mci,
            vc_id=7,
            ocf_flag=False,
            master_ch_frame_count=0,
            vc_frame_count=0,
            frame_datafield_status=dfs,
        )
        tm_frame = TmTransferFrame(9, primary_header, None, b"\x00\x01\x02", None, None)
        packed = tm_frame.pack()
        unpacked = tm_frame.unpack(packed, 9, False)
        self.assertEqual(tm_frame.data_field, unpacked.data_field)
        self.assertEqual(tm_frame.op_ctrl_field, unpacked.op_ctrl_field)
        self.assertEqual(tm_frame.frame_error_control, unpacked.frame_error_control)
