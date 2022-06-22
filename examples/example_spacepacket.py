from spacepackets.ccsds.spacepacket import SpacePacketHeader, PacketTypes


def main():
    print("-- Space Packet examples --")
    spacepacket_header = SpacePacketHeader(
        packet_type=PacketTypes.TC, apid=0x01, seq_count=0, data_len=0
    )
    header_as_bytes = spacepacket_header.pack()
    print(f"Space packet header (hex): [{header_as_bytes.hex(sep=',')}]")


if __name__ == "__main__":
    main()
