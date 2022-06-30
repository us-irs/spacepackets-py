[![package](https://github.com/robamu-org/py-spacepackets/actions/workflows/package.yml/badge.svg)](https://github.com/robamu-org/py-spacepackets/actions/workflows/package.yml)
[![Documentation Status](https://readthedocs.org/projects/spacepackets/badge/?version=latest)](https://spacepackets.readthedocs.io/en/latest/?badge=latest)
[![codecov](https://codecov.io/gh/us-irs/py-spacepackets/branch/main/graph/badge.svg?token=YFLM60LCVI)](https://codecov.io/gh/us-irs/py-spacepackets)
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
- CCSDS File Delivery Protcol (CFDP) packet implementations according to
  [CCSDS Blue Book 727.0-B-5](https://public.ccsds.org/Pubs/727x0b5.pdf).
- Unified Space Data Link Protocol (USLP) frame implementations according to
  [CCSDS Blue Book 732.1-B-2](https://public.ccsds.org/Pubs/732x1b2.pdf).

It also contains various helper modules

- `PusVerificator` module to track the verification of sent telecommands
- PTC and PFC definitions for ECSS packets

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

[This example](https://github.com/robamu-org/py-spacepackets/blob/main/examples/example_pus.py) shows how to generate PUS packets using the PUS ping telecommand and a PUS
ping telemetry reply

## CCSDS Space Packet

[This example](https://github.com/robamu-org/py-spacepackets/blob/main/examples/example_spacepacket.py)
shows how to generate a space packet header:

## USLP Frames

[This example](https://github.com/robamu-org/py-spacepackets/blob/main/examples/example_uslp.py)
shows how to generate a simple variable length USLP frame containing a simple space packet

# Tests

All tests are provided in the `tests` folder and can be run with coverage information
by running

```sh
coverage run -m pytest
```

provided that `pytest` and `coverage` were installed with

```sh
python3 -m pip install coverage pytest
```
