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
