from spacepackets.ccsds.spacepacket import SpacePacketHeader, PacketTypes
from spacepackets.util import get_printable_data_string, PrintFormats


def main():
    print("-- Space Packet examples --")
    spacepacket_header = SpacePacketHeader(
        packet_type=PacketTypes.TC, apid=0x01, source_sequence_count=0, data_length=0
    )
    header_as_bytes = spacepacket_header.pack()
    print_string = get_printable_data_string(
        print_format=PrintFormats.HEX, data=header_as_bytes
    )
    print(f"Space packet header: {print_string}")


if __name__ == "__main__":
    main()
