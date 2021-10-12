from spacepackets.ecss.tc import PusTelecommand
from spacepackets.ecss.tm import PusTelemetry
from spacepackets.util import get_printable_data_string, PrintFormats


def main():
	ping_cmd = PusTelecommand(
		service=17,
		subservice=1,
		apid=0x01
	)
	cmd_as_bytes = ping_cmd.pack()
	print_string = get_printable_data_string(print_format=PrintFormats.HEX, data=cmd_as_bytes)
	print(f'Ping telecommand [17,1]: {print_string}')

	ping_reply = PusTelemetry(
		service=17,
		subservice=2,
		apid=0x01
	)
	tm_as_bytes = ping_reply.pack()
	print_string = get_printable_data_string(print_format=PrintFormats.HEX, data=tm_as_bytes)
	print(f'Ping reply [17,2]: {print_string}')


if __name__ == "__main__":
	main()
