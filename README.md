[![ci](https://github.com/us-irs/py-spacepackets/actions/workflows/ci.yml/badge.svg)](https://github.com/us-irs/py-spacepackets/actions/workflows/ci.yml)
[![Documentation Status](https://readthedocs.org/projects/spacepackets/badge/?version=latest)](https://spacepackets.readthedocs.io/en/latest/?badge=latest)
[![codecov](https://codecov.io/gh/us-irs/spacepackets-py/graph/badge.svg?token=YFLM60LCVI)](https://codecov.io/gh/us-irs/spacepackets-py)
[![PyPI version](https://badge.fury.io/py/spacepackets.svg)](https://badge.fury.io/py/spacepackets)

ECSS and CCSDS Spacepackets
======

This package contains generic implementations for various CCSDS
(Consultative Committee for Space Data Systems) and ECSS
(European Cooperation for Space Standardization) packet standards.

Currently, this includes the following components:

- Space Packet implementation according to
  [CCSDS Blue Book 133.0-B-2](https://public.ccsds.org/Pubs/133x0b2e1.pdf)
- CCSDS CDS short timestamp implementation according to
  [CCSDS 301.0-B-4 3.3](https://public.ccsds.org/Pubs/301x0b4e1.pdf).
- PUS Telecommand and PUS Telemetry implementation according to the
  [ECSS-E-ST-70-41C standard](https://ecss.nl/standard/ecss-e-st-70-41c-space-engineering-telemetry-and-telecommand-packet-utilization-15-april-2016/).
  PUS A (legacy) is supported as well.
- CCSDS File Delivery Protcol (CFDP) packet implementations according to
  [CCSDS Blue Book 727.0-B-5](https://public.ccsds.org/Pubs/727x0b5.pdf).
- Unified Space Data Link Protocol (USLP) frame implementations according to
  [CCSDS Blue Book 732.1-B-2](https://public.ccsds.org/Pubs/732x1b2.pdf).

It also contains various helper modules which are commonly used when working with these standards:

- `PusVerificator` module to track the verification of sent telecommands.
- [PTC and PFC definitions](https://spacepackets.readthedocs.io/en/latest/api/ecss.html#module-spacepackets.ecss.fields) for ECSS packets.
- `Countdown` utility class.
- Sequence counter utility classes.

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

You can find all examples [inside the documentation](https://spacepackets.readthedocs.io/en/latest/examples.html).


# Tests

If you want to run the tests, it is recommended to install `pytest` and `coverage` (optional)
first:

```sh
pip install coverage pytest
```

Running tests regularly:

```sh
pytest
```

Running tests with coverage:

```sh
coverage run -m pytest
```

# Documentation

The documentation is built with Sphinx and new documentation should be written using the
[NumPy format](https://www.sphinx-doc.org/en/master/usage/extensions/example_numpy.html#example-numpy).

Install the required dependencies first:

```sh
pip install -r docs/requirements.txt
```

Then the documentation can be built with

```sh
cd docs
make html
```

You can run the doctests with

```sh
make doctest
```

# Formatting and Linting

Linting:

```sh
ruff check .
```

Formatting:

```sh
ruff format .
```
