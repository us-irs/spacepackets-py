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

CFDP Packets
-----------------

This example shows how to generate the 3 CFDP PDUs which constitute of full
small file transfer.

.. testcode:: cfdp

  from typing import Deque
  from spacepackets.cfdp.conf import ByteFieldU8
  from spacepackets.cfdp.defs import ChecksumType, TransmissionMode
  from spacepackets.cfdp.pdu import (
      MetadataParams,
      MetadataPdu,
      FileDataPdu,
      EofPdu,
      PduConfig,
  )
  from spacepackets.cfdp.pdu.file_data import FileDataParams
  from crcmod.predefined import PredefinedCrc

  LOCAL_ID = ByteFieldU8(1)
  REMOTE_ID = ByteFieldU8(2)

  file_transfer_queue = Deque()
  src_name = "/tmp/src-file.txt"
  dest_name = "/tmp/dest-file.txt"
  file_data = "Hello World!"
  seq_num = ByteFieldU8(0)
  pdu_conf = PduConfig(LOCAL_ID, REMOTE_ID, seq_num, TransmissionMode.UNACKNOWLEDGED)
  metadata_params = MetadataParams(
      True, ChecksumType.CRC_32, len(file_data), src_name, dest_name
  )
  metadata_pdu = MetadataPdu(pdu_conf, metadata_params)

  file_transfer_queue.append(metadata_pdu)

  params = FileDataParams(file_data.encode(), 0)
  fd_pdu = FileDataPdu(pdu_conf, params)

  file_transfer_queue.append(fd_pdu)

  crc_calculator = PredefinedCrc("crc32")
  crc_calculator.update(file_data.encode())
  crc_32 = crc_calculator.digest()
  eof_pdu = EofPdu(pdu_conf, crc_32, len(file_data))
  file_transfer_queue.append(eof_pdu)

  for idx, pdu in enumerate(file_transfer_queue):
      print(f"--- PDU {idx} REPR ---")
      print(pdu)
      print(f"--- PDU {idx} RAW ---")
      print(f"0x[{pdu.pack().hex(sep=',')}]")

Output

.. testoutput:: cfdp

    --- PDU 0 REPR ---
    MetadataPdu(params=MetadataParams(closure_requested=True, checksum_type=<ChecksumType.CRC_32: 3>, file_size=12, source_file_name='/tmp/src-file.txt', dest_file_name='/tmp/dest-file.txt'), options=None, pdu_conf=PduConfig(source_entity_id=ByteFieldU8(val=1, byte_len=1), dest_entity_id=ByteFieldU8(val=2, byte_len=1), transaction_seq_num=ByteFieldU8(val=0, byte_len=1), trans_mode=<TransmissionMode.UNACKNOWLEDGED: 1>, file_flag=<LargeFileFlag.NORMAL: 0>, crc_flag=<CrcFlag.NO_CRC: 0>, direction=<Direction.TOWARDS_RECEIVER: 0>, seg_ctrl=<SegmentationControl.NO_RECORD_BOUNDARIES_PRESERVATION: 0>))
    --- PDU 0 RAW ---
    0x[24,00,2b,00,01,00,02,07,43,00,00,00,0c,11,2f,74,6d,70,2f,73,72,63,2d,66,69,6c,65,2e,74,78,74,12,2f,74,6d,70,2f,64,65,73,74,2d,66,69,6c,65,2e,74,78,74]
    --- PDU 1 REPR ---
    FileDataPdu(params=FileDataParams(file_data=b'Hello World!', offset=0, segment_metadata_flag=<SegmentMetadataFlag.NOT_PRESENT: 0>, record_cont_state=None, segment_metadata=None), pdu_conf=PduConfig(source_entity_id=ByteFieldU8(val=1, byte_len=1), dest_entity_id=ByteFieldU8(val=2, byte_len=1), transaction_seq_num=ByteFieldU8(val=0, byte_len=1), trans_mode=<TransmissionMode.UNACKNOWLEDGED: 1>, file_flag=<LargeFileFlag.NORMAL: 0>, crc_flag=<CrcFlag.NO_CRC: 0>, direction=<Direction.TOWARDS_RECEIVER: 0>, seg_ctrl=<SegmentationControl.NO_RECORD_BOUNDARIES_PRESERVATION: 0>))
    --- PDU 1 RAW ---
    0x[34,00,10,00,01,00,02,00,00,00,00,48,65,6c,6c,6f,20,57,6f,72,6c,64,21]
    --- PDU 2 REPR ---
    EofPdu(file_checksum=b'\x1c)\x1c\xa3',file_size=12, pdu_conf=PduConfig(source_entity_id=ByteFieldU8(val=1, byte_len=1), dest_entity_id=ByteFieldU8(val=2, byte_len=1), transaction_seq_num=ByteFieldU8(val=0, byte_len=1), trans_mode=<TransmissionMode.UNACKNOWLEDGED: 1>, file_flag=<LargeFileFlag.NORMAL: 0>, crc_flag=<CrcFlag.NO_CRC: 0>, direction=<Direction.TOWARDS_RECEIVER: 0>, seg_ctrl=<SegmentationControl.NO_RECORD_BOUNDARIES_PRESERVATION: 0>),fault_location=None,condition_code=0)
    --- PDU 2 RAW ---
    0x[24,00,0a,00,01,00,02,04,00,1c,29,1c,a3,00,00,00,0c]

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


