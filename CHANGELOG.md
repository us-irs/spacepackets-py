Change Log
=======

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

## [unreleased]

## [v0.10.0] 23.06.2022

- New Helper objects for CCSDS Space Packet subfields, namely new
  `PacketId` and `PacketSeqCtrl` class
- Remove PUS A support for PUS telecommands
- Added multiple `__str__` and `__repr__` implementations where
  applicable
- API simplification, shorter or better keywords for PUS TM and PUS TC
  constructor calls

## [v0.9.0]

- API improvements, bugfix and general improvements for CCSDS spacepacket
  header implementation

## [v0.8.1]

- Named value for fetching global APID

## [v0.8.0]

- Update `PusServices` enumeration

## [v0.7.1]

- Added subservice enumerations for generic PUS Services 1, 3, 5 and 17

## [v0.7.0]

- Improvement for API of PUS TM1 and PUS TM17 base classes

## [v0.6.2]

- Fix in size pre-check of space packet parser `parse_space_packets`

## [v0.6.1]

- Add packet sizes in `__str__` method of PUS TM and TC
- Some type corrections: Expect `bytes` instead of `bytearray` where applicable

## [v0.6.0]

### Added

- Unified Space Data Link Protocol Packet implementations


### Changed

- Assign default print format in TM and TC implementation

## [v0.5.4]

- Important bugfix in space packet parser implementation

## [v0.5.3]

- Maximum TC packet size configurable now, will be checked when packaging TC packets.
  Default maximum size is 1004 bytes for now

## [v0.5.2]

- Smaller tweaks for CFDP

## [v0.5.1]

- Applied formatting with the `black` Python formatter
- Small tweaks to the NOTICE file
