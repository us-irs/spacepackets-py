from spacepackets.ecss.tc import PusTelecommand
from spacepackets.ecss.tm import PusTelemetry


def main():
    print("-- PUS packet examples --")
    ping_cmd = PusTelecommand(service=17, subservice=1, apid=0x01)
    cmd_as_bytes = ping_cmd.pack()
    print(f"Ping telecommand [17,1] (hex): [{cmd_as_bytes.hex(sep=',')}]")

    ping_reply = PusTelemetry(service=17, subservice=2, apid=0x01)
    tm_as_bytes = ping_reply.pack()
    print(f"Ping reply [17,2] (hex): [{tm_as_bytes.hex(sep=',')}]")


if __name__ == "__main__":
    main()
