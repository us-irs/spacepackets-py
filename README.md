[![package](https://github.com/robamu-org/py-spacepackets/actions/workflows/package.yml/badge.svg)](https://github.com/robamu-org/py-spacepackets/actions/workflows/package.yml)
[![Documentation Status](https://readthedocs.org/projects/spacepackets/badge/?version=latest)](https://spacepackets.readthedocs.io/en/latest/?badge=latest)
[![codecov](https://codecov.io/gh/robamu-org/py-spacepackets/branch/main/graph/badge.svg?token=YFLM60LCVI)](https://codecov.io/gh/robamu-org/py-spacepackets)
[![PyPI version](https://badge.fury.io/py/spacepackets.svg)](https://badge.fury.io/py/spacepackets)

ECSS and CCSDS Spacepackets
======

This package contains generic implementations for various CCSDS
(Consultative Committee for Space Data Systems) and ECSS
(European Cooperation for Space Standardization) packet standards.

Currently, this includes the following components:

- Space Packet implementation according to
  [CCSDS Blue Book 133.0-B-2](https://public.ccsds.org/Pubs/133x0b2e1.pdf)
- PUS Telecommand and PUS Telemetry implementation according to the
  [ECSS-E-ST-70-41C standard](https://ecss.nl/standard/ecss-e-st-70-41c-space-engineering-telemetry-and-telecommand-packet-utilization-15-april-2016/).
  It supports PUS A as well.
- CCSDS File Delivery Protcol (CFDP) packet implementations according to
  [CCSDS Blue Book 727.0-B-5](https://public.ccsds.org/Pubs/727x0b5.pdf).

# Install

You can install this package from PyPI

Linux:

```sh
python3 -m pip install spacepackets
```

Windows:

```sh
py -m pip install spacepackets
```

# Examples

You can find all examples listed here in the `example` folder as well.

## ECSS PUS Packets

This examples shows how to generate PUS packets using the PUS ping telecommand and a PUS
ping telemetry reply.

```py
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
```

## CCSDS Space Packet

This example shows how to generate a space packet header

```py
from spacepackets.ccsds.spacepacket import SpacePacketHeader, PacketTypes
from spacepackets.util import get_printable_data_string, PrintFormats


def main():
    spacepacket_header = SpacePacketHeader(
        packet_type=PacketTypes.TC,
        apid=0x01,
        source_sequence_count=0,
        data_length=0
    )
    header_as_bytes = spacepacket_header.pack()
    print_string = get_printable_data_string(print_format=PrintFormats.HEX, data=header_as_bytes)
    print(f'Space packet header: {print_string}')


if __name__ == "__main__":
    main()
```