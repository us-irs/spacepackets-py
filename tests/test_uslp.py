from unittest import TestCase
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
    UslpVersionMissmatch
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
            vcf_count=0,
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

        unpacked_primary_header = PrimaryHeader.unpack(raw_packet=packed_header)
        # Check field validity by serializing unpacked header again
        self.assertEqual(packed_header, unpacked_primary_header.pack())
        self.assertRaises(
            UslpTypeMissmatch, TruncatedPrimaryHeader.unpack, packed_header
        )
        self.assertRaises(
            UslpInvalidRawPacketOrFrameLen, TruncatedPrimaryHeader.unpack, bytearray()
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

    def test_uslp(self):
        pass
