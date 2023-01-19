from unittest import TestCase

from spacepackets.uslp.defs import (
    UslpFhpVhopFieldMissing,
    UslpInvalidConstructionRules,
    UslpInvalidFrameHeader,
    UslpTruncatedFrameNotAllowed,
)
from spacepackets.uslp.header import (
    TruncatedPrimaryHeader,
    PrimaryHeader,
    SourceOrDestField,
    ProtocolCommandFlag,
    BypassSequenceControlFlag,
    determine_header_type,
    HeaderType,
    UslpTypeMissmatch,
    UslpInvalidRawPacketOrFrameLen,
    UslpVersionMissmatch,
)

from spacepackets.uslp.frame import (
    TransferFrame,
    TransferFrameDataField,
    TfdzConstructionRules,
    UslpProtocolIdentifier,
    FrameType,
    FixedFrameProperties,
    VarFrameProperties,
)


class TestUslp(TestCase):
    def test_header(self):
        primary_header = PrimaryHeader(
            scid=pow(2, 16) - 2,
            map_id=0b0011,
            src_dest=SourceOrDestField.SOURCE,
            vcid=0b110111,
            frame_len=pow(2, 16) - 3,
            op_ctrl_flag=True,
            vcf_count_len=0,
            prot_ctrl_cmd_flag=ProtocolCommandFlag.PROTOCOL_INFORMATION,
            bypass_seq_ctrl_flag=BypassSequenceControlFlag.EXPEDITED_QOS,
        )
        self.assertEqual(primary_header.truncated(), False)
        self.assertEqual(primary_header.len(), 7)
        packed_header = primary_header.pack()
        self.assertEqual((packed_header[0] >> 4) & 0b1111, 0x0C)
        # First four bits of SCID should be all ones
        self.assertEqual((packed_header[0] & 0x0F), 0b1111)
        # Next eight bits should be all ones
        self.assertEqual(packed_header[1], 0xFF)
        # Last four bits should be 0b1110
        self.assertEqual((packed_header[2] >> 4) & 0b1111, 0b1110)
        # Source or destination ID, should be 0
        self.assertEqual((packed_header[2] >> 3) & 0x01, 0)
        # The next three bits are the first three bits of the virtual channel
        self.assertEqual(packed_header[2] & 0b111, 0b110)
        # The first three bits of the next byte are the last three bits of the virtual channel
        self.assertEqual((packed_header[3] >> 5) & 0b111, 0b111)
        # The next four bits are the map ID
        self.assertEqual((packed_header[3] >> 1) & 0b1111, 0b0011)
        # End of frame primary header. Should be 0 for non-trucated frame
        self.assertEqual(packed_header[3] & 0x01, 0)
        # Frame length is 0xfffd
        self.assertEqual(packed_header[4], 0xFF)
        self.assertEqual(packed_header[5], 0xFD)
        # Bypass / Sequence Control is 1
        self.assertEqual((packed_header[6] >> 7) & 0x01, 1)
        # Protocol Control Command Flag is 1
        self.assertEqual((packed_header[6] >> 6) & 0x01, 1)
        # Spares are 0
        self.assertEqual((packed_header[6] >> 4) & 1, 0b00)
        # OCF flag is 1
        self.assertEqual((packed_header[6] >> 3) & 1, 1)
        # VCF frame count is 0
        self.assertEqual(packed_header[6] & 0b111, 0)
        self.assertEqual(determine_header_type(packed_header), HeaderType.NON_TRUNCATED)

        primary_header.vcf_count_len = 1
        self.assertRaises(ValueError, primary_header.pack)
        primary_header.vcf_count = 0xAF
        header_with_vcf_count = primary_header.pack()
        self.assertEqual(header_with_vcf_count[6] & 0b111, 0x01)
        self.assertEqual(header_with_vcf_count[7], 0xAF)
        primary_header.vcf_count_len = 2
        primary_header.vcf_count = 0xAFFE
        unpacked_vcf_1 = PrimaryHeader.unpack(raw_packet=header_with_vcf_count)
        self.assertEqual(unpacked_vcf_1.vcf_count_len, 1)
        self.assertEqual(unpacked_vcf_1.vcf_count, 0xAF)

        header_with_vcf_count = primary_header.pack()
        self.assertEqual(header_with_vcf_count[6] & 0b111, 2)
        self.assertEqual(header_with_vcf_count[7], 0xAF)
        self.assertEqual(header_with_vcf_count[8], 0xFE)
        unpacked_vcf_2 = PrimaryHeader.unpack(raw_packet=header_with_vcf_count)
        self.assertEqual(unpacked_vcf_2.vcf_count_len, 2)
        self.assertEqual(unpacked_vcf_2.vcf_count, 0xAFFE)

        primary_header.vcf_count_len = 3
        primary_header.vcf_count = 0xAFFEFE
        header_with_vcf_count = primary_header.pack()
        self.assertEqual(header_with_vcf_count[6] & 0b111, 3)
        self.assertEqual(header_with_vcf_count[7], 0xAF)
        self.assertEqual(header_with_vcf_count[8], 0xFE)
        self.assertEqual(header_with_vcf_count[9], 0xFE)
        unpacked_vcf_3 = PrimaryHeader.unpack(raw_packet=header_with_vcf_count)
        self.assertEqual(unpacked_vcf_3.vcf_count_len, 3)
        self.assertEqual(unpacked_vcf_3.vcf_count, 0xAFFEFE)

        primary_header.vcf_count_len = 4
        primary_header.vcf_count = 0xAFFECAFE
        header_with_vcf_count = primary_header.pack()
        self.assertEqual(header_with_vcf_count[6] & 0b111, 4)
        self.assertEqual(header_with_vcf_count[7], 0xAF)
        self.assertEqual(header_with_vcf_count[8], 0xFE)
        self.assertEqual(header_with_vcf_count[9], 0xCA)
        self.assertEqual(header_with_vcf_count[10], 0xFE)
        unpacked_vcf_4 = PrimaryHeader.unpack(raw_packet=header_with_vcf_count)
        self.assertEqual(unpacked_vcf_4.vcf_count_len, 4)
        self.assertEqual(unpacked_vcf_4.vcf_count, 0xAFFECAFE)

        primary_header.vcf_count_len = 7
        primary_header.vcf_count = 0xAFFECAFEBABEAF
        header_with_vcf_count = primary_header.pack()
        self.assertEqual(header_with_vcf_count[6] & 0b111, 7)
        self.assertEqual(header_with_vcf_count[7], 0xAF)
        self.assertEqual(header_with_vcf_count[8], 0xFE)
        self.assertEqual(header_with_vcf_count[9], 0xCA)
        self.assertEqual(header_with_vcf_count[10], 0xFE)
        self.assertEqual(header_with_vcf_count[11], 0xBA)
        self.assertEqual(header_with_vcf_count[12], 0xBE)
        self.assertEqual(header_with_vcf_count[13], 0xAF)
        unpacked_with_vcf = PrimaryHeader.unpack(raw_packet=header_with_vcf_count)
        self.assertEqual(unpacked_with_vcf.vcf_count_len, 7)
        self.assertEqual(unpacked_with_vcf.vcf_count, 0xAFFECAFEBABEAF)
        unpacked_primary_header = PrimaryHeader.unpack(raw_packet=packed_header)
        # Check field validity by serializing unpacked header again
        self.assertEqual(packed_header, unpacked_primary_header.pack())
        self.assertRaises(
            UslpTypeMissmatch, TruncatedPrimaryHeader.unpack, packed_header
        )
        self.assertRaises(
            UslpInvalidRawPacketOrFrameLen, TruncatedPrimaryHeader.unpack, bytearray()
        )
        self.assertRaises(
            UslpInvalidRawPacketOrFrameLen,
            PrimaryHeader.unpack,
            header_with_vcf_count[0:7],
        )
        crap_with_valid_parsing_fields = bytearray(5)
        crap_with_valid_parsing_fields[0] = 0b11000000
        self.assertRaises(
            UslpInvalidRawPacketOrFrameLen,
            PrimaryHeader.unpack,
            crap_with_valid_parsing_fields,
        )
        # Set invalid version
        crap_with_valid_parsing_fields[0] = 0b0001000
        crap_with_valid_parsing_fields.extend(bytearray(3))
        self.assertRaises(
            UslpVersionMissmatch,
            PrimaryHeader.unpack,
            crap_with_valid_parsing_fields,
        )
        truncated_header = TruncatedPrimaryHeader(
            scid=0b0001000100010001,
            map_id=0b1101,
            vcid=0b101101,
            src_dest=SourceOrDestField.DEST,
        )
        self.assertEqual(truncated_header.truncated(), True)
        self.assertEqual(truncated_header.len(), 4)
        packed_header = truncated_header.pack()
        self.assertEqual((packed_header[0] >> 4) & 0b1111, 0x0C)
        self.assertEqual((packed_header[0] & 0x0F), 0b0001)
        self.assertEqual(packed_header[1], 0b00010001)
        self.assertEqual((packed_header[2] >> 4) & 0b1111, 0b0001)
        # source or dest ID is 1
        self.assertEqual((packed_header[2] >> 3) & 0x01, 1)
        # The next three bits are the first three bits of the virtual channel
        self.assertEqual(packed_header[2] & 0b111, 0b101)
        # The first three bits of the next byte are the last three bits of the virtual channel
        self.assertEqual((packed_header[3] >> 5) & 0b111, 0b101)
        # The next four bits are the map ID
        self.assertEqual((packed_header[3] >> 1) & 0b1111, 0b1101)
        # End of frame primary header. Should be 1 for truncated frame
        self.assertEqual(packed_header[3] & 0x01, 1)
        self.assertEqual(determine_header_type(packed_header), HeaderType.TRUNCATED)

        self.assertRaises(ValueError, determine_header_type, bytearray())
        tmp = truncated_header.vcid
        truncated_header.vcid = 0xFFF
        self.assertRaises(ValueError, truncated_header.pack)
        truncated_header.vcid = tmp
        tmp = truncated_header.scid
        truncated_header.scid = 0xFFFFF
        self.assertRaises(ValueError, truncated_header.pack)
        truncated_header.scid = tmp
        tmp = truncated_header.map_id
        truncated_header.map_id = 0xFFFFF
        self.assertRaises(ValueError, truncated_header.pack)
        truncated_header.map_id = tmp
        unpacked_truncated = TruncatedPrimaryHeader.unpack(raw_packet=packed_header)
        self.assertEqual(unpacked_truncated.pack(), packed_header)

    def test_frame(self):
        # Initialize with frame length 0 and set frame length field later with a helper function
        primary_header = PrimaryHeader(
            scid=0x10,
            map_id=0b0011,
            src_dest=SourceOrDestField.SOURCE,
            vcid=0b110111,
            frame_len=0,
            op_ctrl_flag=False,
            vcf_count_len=0,
            prot_ctrl_cmd_flag=ProtocolCommandFlag.USER_DATA,
            bypass_seq_ctrl_flag=BypassSequenceControlFlag.SEQ_CTRLD_QOS,
        )
        fp_tfdf = TransferFrameDataField(
            tfdz_cnstr_rules=TfdzConstructionRules.FpPacketSpanningMultipleFrames,
            uslp_ident=UslpProtocolIdentifier.SPACE_PACKETS_ENCAPSULATION_PACKETS,
            tfdz=bytearray(),
            fhp_or_lvop=0,
        )
        # Packet without op control field, without insert zone and without frame error control
        transfer_frame = TransferFrame(
            header=primary_header,
            op_ctrl_field=None,
            insert_zone=None,
            tfdf=fp_tfdf,
            fecf=None,
        )
        # This sets the correct frame length in the primary header
        transfer_frame.set_frame_len_in_header()
        frame_packed = transfer_frame.pack(truncated=False, frame_type=FrameType.FIXED)
        # 7 byte primary header + TFDF with 3 bytes, TFDZ is empty
        self.assertEqual(len(frame_packed), 10)
        self.assertEqual(
            (frame_packed[4] << 8) | frame_packed[5], len(frame_packed) - 1
        )
        # The primary header was already unit-tested, its fields won't be checked again
        self.assertEqual(frame_packed[7], 0x00)
        self.assertEqual(frame_packed[8], 0x00)
        self.assertEqual(frame_packed[9], 0x00)
        transfer_frame.tfdf.tfdz_contr_rules = (
            TfdzConstructionRules.FpFixedStartOfMapaSDU
        )
        transfer_frame.tfdf.uslp_ident = UslpProtocolIdentifier.IDLE_DATA
        transfer_frame.tfdf.fhp_or_lvop = 0xAFFE
        frame_packed = transfer_frame.pack()
        self.assertEqual(len(frame_packed), 10)
        self.assertEqual(
            (frame_packed[4] << 8) | frame_packed[5], len(frame_packed) - 1
        )
        # TFDZ construction rule is 0b001, USLP identifier is 0b11111, concatenation is 0x3f
        self.assertEqual(frame_packed[7], 0x3F)
        # This pointer does not really make sense for an empty TFDZ, but we just check that is was
        # still set correctly
        self.assertEqual(frame_packed[8], 0xAF)
        self.assertEqual(frame_packed[9], 0xFE)
        frame_properties = FixedFrameProperties(
            has_insert_zone=False, has_fecf=False, fixed_len=10
        )
        frame_unpacked = TransferFrame.unpack(
            raw_frame=frame_packed,
            frame_type=FrameType.FIXED,
            frame_properties=frame_properties,
        )
        self.assertEqual(frame_unpacked.insert_zone, None)
        self.assertEqual(frame_unpacked.fecf, None)
        self.assertEqual(frame_unpacked.op_ctrl_field, None)
        self.assertEqual(
            frame_unpacked.tfdf.uslp_ident, UslpProtocolIdentifier.IDLE_DATA
        )
        self.assertEqual(
            frame_unpacked.tfdf.tfdz_contr_rules,
            TfdzConstructionRules.FpFixedStartOfMapaSDU,
        )
        self.assertEqual(frame_unpacked.tfdf.fhp_or_lvop, 0xAFFE)
        self.assertEqual(frame_unpacked.tfdf.tfdz, bytearray())
        self.assertEqual(frame_unpacked.header.pack(), transfer_frame.header.pack())
        with self.assertRaises(ValueError):
            FixedFrameProperties(fixed_len=5, has_fecf=False, has_insert_zone=True)
        with self.assertRaises(ValueError):
            FixedFrameProperties(fixed_len=5, has_fecf=True, has_insert_zone=False)
        with self.assertRaises(ValueError):
            invalid_tfdz = bytearray(70000)
            tfdf = TransferFrameDataField(
                tfdz_cnstr_rules=TfdzConstructionRules.FpPacketSpanningMultipleFrames,
                uslp_ident=UslpProtocolIdentifier.SPACE_PACKETS_ENCAPSULATION_PACKETS,
                tfdz=invalid_tfdz,
                fhp_or_lvop=0,
            )
        self.assertEqual(fp_tfdf.verify_frame_type(frame_type=FrameType.FIXED), True)
        self.assertEqual(
            fp_tfdf.verify_frame_type(frame_type=FrameType.VARIABLE), False
        )
        vp_tfdf = TransferFrameDataField(
            tfdz_cnstr_rules=TfdzConstructionRules.VpNoSegmentation,
            uslp_ident=UslpProtocolIdentifier.SPACE_PACKETS_ENCAPSULATION_PACKETS,
            tfdz=bytearray(),
        )
        self.assertEqual(vp_tfdf.verify_frame_type(frame_type=FrameType.VARIABLE), True)
        self.assertEqual(
            vp_tfdf.should_have_fhp_or_lvp_field(
                truncated=False, frame_type=FrameType.VARIABLE
            ),
            False,
        )
        self.assertEqual(
            fp_tfdf.should_have_fhp_or_lvp_field(
                truncated=False, frame_type=FrameType.FIXED
            ),
            True,
        )
        empty_short_tfdf = TransferFrameDataField(
            tfdz_cnstr_rules=TfdzConstructionRules.FpPacketSpanningMultipleFrames,
            uslp_ident=UslpProtocolIdentifier.SPACE_PACKETS_ENCAPSULATION_PACKETS,
            fhp_or_lvop=0,
            tfdz=bytearray(),
        )
        packed_short_tfdf = empty_short_tfdf.pack(
            truncated=False, frame_type=FrameType.FIXED
        )
        self.assertEqual(len(packed_short_tfdf), 3)
        TransferFrameDataField.unpack(
            raw_tfdf=packed_short_tfdf,
            frame_type=FrameType.FIXED,
            truncated=False,
            exact_len=3,
        )

        tfdf_vp = TransferFrameDataField(
            tfdz_cnstr_rules=TfdzConstructionRules.VpLastSegment,
            uslp_ident=UslpProtocolIdentifier.SPACE_PACKETS_ENCAPSULATION_PACKETS,
            tfdz=bytearray(),
        )
        tfdf_vp_packed = tfdf_vp.pack()
        with self.assertRaises(UslpFhpVhopFieldMissing):
            TransferFrameDataField(
                tfdz_cnstr_rules=TfdzConstructionRules.FpFixedStartOfMapaSDU,
                uslp_ident=UslpProtocolIdentifier.SPACE_PACKETS_ENCAPSULATION_PACKETS,
                tfdz=bytearray(),
            ).pack()
        with self.assertRaises(UslpInvalidRawPacketOrFrameLen):
            TransferFrameDataField.unpack(
                raw_tfdf=bytearray(),
                truncated=False,
                exact_len=0,
                frame_type=FrameType.FIXED,
            )
        with self.assertRaises(UslpInvalidConstructionRules):
            short_tfdf = empty_short_tfdf.pack()
            short_tfdf[0] &= ~0b11100000
            short_tfdf[0] |= TfdzConstructionRules.VpNoSegmentation << 5
            TransferFrameDataField.unpack(
                raw_tfdf=short_tfdf,
                frame_type=FrameType.FIXED,
                exact_len=1,
                truncated=False,
            )
        tfdf_vp_unpacked = TransferFrameDataField.unpack(
            raw_tfdf=tfdf_vp_packed,
            frame_type=FrameType.VARIABLE,
            exact_len=len(tfdf_vp_packed),
            truncated=False,
        )
        self.assertEqual(tfdf_vp_unpacked.tfdz, bytearray())
        self.assertEqual(
            tfdf_vp_unpacked.uslp_ident,
            UslpProtocolIdentifier.SPACE_PACKETS_ENCAPSULATION_PACKETS,
        )
        self.assertEqual(
            tfdf_vp_unpacked.tfdz_contr_rules, TfdzConstructionRules.VpLastSegment
        )
        primary_header = PrimaryHeader(
            scid=0x10,
            map_id=0b0011,
            src_dest=SourceOrDestField.SOURCE,
            vcid=0b110111,
            frame_len=0,
            op_ctrl_flag=True,
            vcf_count_len=0,
            prot_ctrl_cmd_flag=ProtocolCommandFlag.USER_DATA,
            bypass_seq_ctrl_flag=BypassSequenceControlFlag.SEQ_CTRLD_QOS,
        )
        tfdf = TransferFrameDataField(
            tfdz_cnstr_rules=TfdzConstructionRules.FpPacketSpanningMultipleFrames,
            uslp_ident=UslpProtocolIdentifier.SPACE_PACKETS_ENCAPSULATION_PACKETS,
            tfdz=bytearray([1, 2, 3, 4]),
            fhp_or_lvop=0,
        )
        insert_zone = bytearray(4)
        op_ctrl_field = bytearray([1, 2, 3, 4])
        fecf = bytearray([3, 4])
        larger_frame = TransferFrame(
            header=primary_header,
            insert_zone=insert_zone,
            op_ctrl_field=op_ctrl_field,
            tfdf=tfdf,
            fecf=fecf,
        )
        larger_frame.set_frame_len_in_header()
        self.assertEqual(larger_frame.header.frame_len, 24 - 1)
        self.assertEqual(larger_frame.len(), 24)
        larger_frame_packed = larger_frame.pack()
        self.assertEqual(len(larger_frame_packed), 24)
        self.assertEqual(larger_frame_packed[7 : 7 + 4], bytearray(4))
        self.assertEqual(larger_frame_packed[14 : 14 + 4], bytearray([1, 2, 3, 4]))
        self.assertEqual(larger_frame_packed[18 : 18 + 4], bytearray([1, 2, 3, 4]))
        self.assertEqual(larger_frame_packed[22:], bytearray([3, 4]))
        with self.assertRaises(UslpInvalidRawPacketOrFrameLen):
            TransferFrame.unpack(
                raw_frame=larger_frame_packed,
                frame_type=FrameType.FIXED,
                frame_properties=FixedFrameProperties(
                    fixed_len=28,
                    has_insert_zone=True,
                    insert_zone_len=4,
                    has_fecf=True,
                    fecf_len=2,
                ),
            )
        with self.assertRaises(UslpInvalidRawPacketOrFrameLen):
            TransferFrame.unpack(
                raw_frame=larger_frame_packed,
                frame_type=FrameType.FIXED,
                frame_properties=FixedFrameProperties(
                    fixed_len=22,
                    has_insert_zone=True,
                    insert_zone_len=4,
                    has_fecf=True,
                    fecf_len=2,
                ),
            )
        with self.assertRaises(ValueError):
            TransferFrame.unpack(
                raw_frame=larger_frame_packed,
                frame_type=FrameType.FIXED,
                frame_properties=VarFrameProperties(
                    truncated_frame_len=12,
                    has_insert_zone=True,
                    insert_zone_len=4,
                    has_fecf=True,
                    fecf_len=2,
                ),
            )
        larger_frame.header.op_ctrl_flag = False
        with self.assertRaises(UslpInvalidFrameHeader):
            larger_frame.pack()
        larger_frame.header.op_ctrl_flag = True
        larger_frame.op_ctrl_field = None
        with self.assertRaises(UslpInvalidFrameHeader):
            larger_frame.pack()
        larger_frame.header.op_ctrl_flag = True
        # Invalid length
        larger_frame.op_ctrl_field = bytearray([0, 0, 0])
        with self.assertRaises(ValueError):
            larger_frame.pack()
        larger_frame_unpacked = TransferFrame.unpack(
            raw_frame=larger_frame_packed,
            frame_type=FrameType.FIXED,
            frame_properties=FixedFrameProperties(
                fixed_len=24,
                has_insert_zone=True,
                insert_zone_len=4,
                has_fecf=True,
                fecf_len=2,
            ),
        )
        self.assertEqual(larger_frame_unpacked.fecf, bytearray([3, 4]))
        self.assertEqual(larger_frame_unpacked.insert_zone, bytearray(4))
        self.assertEqual(larger_frame_unpacked.op_ctrl_field, bytearray([1, 2, 3, 4]))
        with self.assertRaises(UslpInvalidRawPacketOrFrameLen):
            TransferFrame.unpack(
                raw_frame=bytearray(3),
                frame_type=FrameType.FIXED,
                frame_properties=FixedFrameProperties(
                    fixed_len=24,
                    has_insert_zone=True,
                    insert_zone_len=4,
                    has_fecf=True,
                    fecf_len=2,
                ),
            )
        truncated_header = TruncatedPrimaryHeader(
            scid=12, src_dest=SourceOrDestField.SOURCE, map_id=12, vcid=5
        )
        tfdf_truncated = TransferFrameDataField(
            tfdz_cnstr_rules=TfdzConstructionRules.VpNoSegmentation,
            uslp_ident=UslpProtocolIdentifier.SPACE_PACKETS_ENCAPSULATION_PACKETS,
            tfdz=bytearray([1, 2, 3, 4]),
        )
        truncated_frame = TransferFrame(
            header=truncated_header,
            insert_zone=None,
            op_ctrl_field=None,
            tfdf=tfdf_truncated,
            fecf=None,
        )
        truncated_frame_packed = truncated_frame.pack(truncated=True)
        self.assertEqual(len(truncated_frame_packed), 9)
        with self.assertRaises(UslpTruncatedFrameNotAllowed):
            TransferFrame.unpack(
                raw_frame=truncated_frame_packed,
                frame_type=FrameType.FIXED,
                frame_properties=FixedFrameProperties(
                    fixed_len=len(truncated_frame_packed),
                    has_insert_zone=True,
                    insert_zone_len=4,
                    has_fecf=True,
                    fecf_len=2,
                ),
            )
        truncated_frame_unpacked = TransferFrame.unpack(
            raw_frame=truncated_frame_packed,
            frame_type=FrameType.VARIABLE,
            frame_properties=VarFrameProperties(
                truncated_frame_len=9, has_insert_zone=False, has_fecf=False
            ),
        )
        self.assertEqual(truncated_frame_unpacked.tfdf.fhp_or_lvop, None)
        self.assertEqual(
            truncated_frame_unpacked.tfdf.uslp_ident,
            UslpProtocolIdentifier.SPACE_PACKETS_ENCAPSULATION_PACKETS,
        )
        self.assertEqual(
            truncated_frame_unpacked.tfdf.tfdz_contr_rules,
            TfdzConstructionRules.VpNoSegmentation,
        )
