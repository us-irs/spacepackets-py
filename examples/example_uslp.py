from spacepackets.uslp.header import (
    PrimaryHeader,
    SourceOrDestField,
    ProtocolCommandFlag,
    BypassSequenceControlFlag,
)
from spacepackets.uslp.frame import (
    TransferFrame,
    TransferFrameDataField,
    TfdzConstructionRules,
    UslpProtocolIdentifier,
)
from spacepackets.ccsds.spacepacket import SpacePacketHeader, PacketTypes, SequenceFlags

SPACECRAFT_ID = 0x73


def main():
    print("-- USLP frame example --")
    frame_header = PrimaryHeader(
        scid=SPACECRAFT_ID,
        map_id=0,
        vcid=1,
        src_dest=SourceOrDestField.SOURCE,
        frame_len=0,
        vcf_count_len=0,
        op_ctrl_flag=False,
        prot_ctrl_cmd_flag=ProtocolCommandFlag.USER_DATA,
        bypass_seq_ctrl_flag=BypassSequenceControlFlag.SEQ_CTRLD_QOS,
    )
    data = bytearray([1, 2, 3, 4])
    # Wrap the data into a space packet
    space_packet_wrapper = SpacePacketHeader(
        packet_type=PacketTypes.TC,
        sequence_flags=SequenceFlags.UNSEGMENTED,
        apid=SPACECRAFT_ID,
        data_length=len(data) - 1,
        ssc=0,
    )
    tfdz = space_packet_wrapper.pack() + data
    tfdf = TransferFrameDataField(
        tfdz_cnstr_rules=TfdzConstructionRules.VpNoSegmentation,
        uslp_ident=UslpProtocolIdentifier.SPACE_PACKETS_ENCAPSULATION_PACKETS,
        tfdz=tfdz,
    )
    var_frame = TransferFrame(header=frame_header, tfdf=tfdf)
    var_frame_packed = var_frame.pack()
    print(
        f"USLP variable length frame without FECF, and Operation Control Field containing a "
        f"simple space packet: {var_frame_packed.hex(sep=',')}"
    )


if __name__ == "__main__":
    main()
