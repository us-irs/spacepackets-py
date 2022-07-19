Change Log
=======

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

## [unreleased]

## [v0.13.0rc3] 19.07.2022

- Refactored and improved TLV API and handling. Implementation is also a bit more efficient
- Basic CFDP version support: Sanity checks on version field. Only version 2 supported

## [v0.13.0rc2] 12.07.2022

- Improved documentation, first docstrings
- Added more re-exports, for example for the `ccsds` module
- Added several dunder method implementations, especially `__repr__`, `__str__` and `__eq__`
- Improved CFDP packet stack API, several improvements derived from the implementation
  of a CFDP handler using it
- Added generic abstraction for CFDP File Data and File Directive PDUs in form of the
  `AbstractPduBase` and `AbstractFileDirectiveBase`
- Generic `UnsignedByteField` implementation. This is a data structure which is regularly
  used for something like variable sized identifier fields. It provides a lot of boilerplate
  code like common dunder implementations
- Split up and improve test structure a bit

## [v0.13.0rc1] 01.07.2022

- Update `pyproject.toml` file for full support, but still keep `setup.cfg` for now
- API improvements for PUS Verificator
- Setter properties for sequence count and APID in ECSS module
- Make `as_u32` function of `RequestId` public

## [v0.12.1] 30.06.2022

- Small bugfix for PUS 1 Step ID unpacking

## [v0.12.0] 30.06.2022

- Added `PusVerificator` module which can track the verification status of sent telecommands
- Added several magic method implementations, notably `__eq__` and `__hash__` where 
  applicable
- Removed PUS A support completely. PUS A is relatively old, and specialicing on one packet version
  makes the code a lot simpler
- Added `ecss.fields` module which contains the `Ptc` and various PFC enumerations. Also add
  a generic abstraction for enumerated fields in form of a `PacketFieldEnum` and a
  `PacketFieldBase`. This is useful to have an abstraction for the various PUS standard packet
  fields which can have variable sizes

## [v0.11.0] 28.06.2022

- Minor name change for PUS 17 and PUS 1 TM classes
- New `RequestId` class to encapsulate the field used by the PUS 1 Verification
  service
- Update CRC16 handling for TMTC PUS classes. It is possible to calculate the CRC16
  manually with a dedicated `calc_crc` call and then omit the calculation in
  the `pack` call with an additional argument.

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
