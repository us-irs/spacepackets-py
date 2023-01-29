Examples
=========

ECSS PUS packets
-----------------

The following example shows how to generate PUS packets using the PUS ping telecommand and a
PUS ping telemetry reply without a timestamp.

.. testcode:: pus

    from spacepackets.ecss.tc import PusTelecommand
    from spacepackets.ecss.tm import PusTelemetry

    ping_cmd = PusTelecommand(service=17, subservice=1, apid=0x01)
    cmd_as_bytes = ping_cmd.pack()
    print(f"Ping telecommand [17,1] (hex): [{cmd_as_bytes.hex(sep=',')}]")

    ping_reply = PusTelemetry(service=17, subservice=2, apid=0x01, time_provider=None)
    tm_as_bytes = ping_reply.pack()
    print(f"Ping reply [17,2] (hex): [{tm_as_bytes.hex(sep=',')}]")

Output:

.. testoutput:: pus

    Ping telecommand [17,1] (hex): [18,01,c0,00,00,06,2f,11,01,00,00,16,1d]
    Ping reply [17,2] (hex): [08,01,c0,00,00,08,20,11,02,00,00,00,00,86,d7]

CCSDS Space Packet
-------------------

The following example shows how to generate a space packet header:

.. testcode:: ccsds

    from spacepackets.ccsds.spacepacket import SpacePacketHeader, PacketType

    spacepacket_header = SpacePacketHeader(
        packet_type=PacketType.TC, apid=0x01, seq_count=0, data_len=0
    )
    header_as_bytes = spacepacket_header.pack()
    print(f"Space packet header (hex): [{header_as_bytes.hex(sep=',')}]")

Output:

.. testoutput:: ccsds

    Space packet header (hex): [10,01,c0,00,00,00]

USLP Frames
-------------------

This example shows how to generate a simple variable length USLP frame containing a simple space
packet.

.. testcode:: uslp

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
    from spacepackets.ccsds.spacepacket import SpacePacketHeader, PacketType, SequenceFlags

    SPACECRAFT_ID = 0x73

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
        packet_type=PacketType.TC,
        seq_flags=SequenceFlags.UNSEGMENTED,
        apid=SPACECRAFT_ID,
        data_len=len(data) - 1,
        seq_count=0,
    )
    tfdz = space_packet_wrapper.pack() + data
    tfdf = TransferFrameDataField(
        tfdz_cnstr_rules=TfdzConstructionRules.VpNoSegmentation,
        uslp_ident=UslpProtocolIdentifier.SPACE_PACKETS_ENCAPSULATION_PACKETS,
        tfdz=tfdz,
    )
    var_frame = TransferFrame(header=frame_header, tfdf=tfdf)
    var_frame_packed = var_frame.pack()
    print("USLP variable length frame without FECF containing a simple space packet")
    print(f"Contained space packet (hex): [{var_frame_packed.hex(sep=',')}]")

Output:

.. testoutput:: uslp

    USLP variable length frame without FECF containing a simple space packet
    Contained space packet (hex): [c0,07,30,20,00,00,00,e0,10,73,c0,00,00,03,01,02,03,04]
