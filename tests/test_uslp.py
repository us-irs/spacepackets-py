from unittest import TestCase
from spacepackets.uslp.header import (
    TruncatedPrimaryHeader,
    PrimaryHeader,
    SourceOrDestField,
    ProtocolCommandFlag,
    BypassSequenceControlFlag,
)


class TestUslp(TestCase):
    def test_header(self):
        primary_header = PrimaryHeader(
            scid=1,
            map_id=0b0011,
            src_dest=SourceOrDestField.SOURCE,
            vcid=12,
            frame_len=22,
            op_ctrl_flag=False,
            vcf_count_len=0,
            prot_ctrl_cmd_flag=ProtocolCommandFlag.USER_DATA,
            bypass_seq_ctrl_flag=BypassSequenceControlFlag.SEQ_CTRLD_QOS,
            vcf_count=0,
        )
        packed_header = primary_header.pack()
        print(packed_header.hex(sep=','))

        truncated_header = TruncatedPrimaryHeader(
            scid=6,
            map_id=0b1101,
            vcid=0b110111,
            src_dest=SourceOrDestField.DEST
        )
        packed_header = truncated_header.pack()
        print(packed_header.hex(sep=','))

    def test_uslp(self):
        pass
