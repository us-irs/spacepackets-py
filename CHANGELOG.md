Change Log
=======

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

# [unreleased]

# [v0.14.0] 2023-02-09

## Changed

- The CRC16 function retrieved from `crcmod` is now cached on module
  level instead of being re-created for every usage. This might yield
  performance improvements.
- Remove `setup.cfg` and fully move to `pyproject.toml`. The `flake8` config
  was moved to a `.flake8` file.

## Fixed

- The `crc16` property of both `spacepackets.ecss.tc.PusTelecommand`
  and `spacepackets.ecss.tm.PusTelemetry` still was an `int` in some cases.
  It should always be an `Optional[bytes]` (size 2) now.

# [v0.14.0rc3] 2023-02-02

Refactored `logging` module usage to be more pythonic.

## Added

- New `spacepackets.exceptions` module with new generic exception `BytesTooShortError` for errors
  where the object creation from a raw byte stream fails.
- `spacepackets.get_lib_logger` to get access to the library root logger
- `spacepackets.ecss.tc.PusTelecommand`: `empty` constructor
- `spacepackets.ecss.tm.PusTelemetry`: `empty` constructor

## Changed

- (breaking): All `unpack` APIs now consistently expect use the `data` keyword argument
- (possibly breaking): The `spacepackets.ecss.tc.PusTelecommand` now throws the
  `InvalidTcCrc16` exception if an invalid CRC16 is detected.
- (possibly breaking): The `spacepackets.ecss.tm.PusTelemetry` now throws the
  `InvalidTmCrc16` exception if an invalid CRC16 is detected.
- (possibly breaking): `spacepackets.ecss.tc.PusTelecommand` and
  `spacepackets.ecss.tm.PusTelemetry`: The `calc_crc` keyword argument for `pack` has been renamed
  to `recalc_crc`.
- (breaking): The `crc16` proprerty will now return a `Optional[bytes]` object instead of an
  integer.
- `PusTmSecondaryHeader.HEADER_SIZE` renamed to `PusTmSecondaryHeader.MIN_LEN` to better reflect
  the header can actually be larger if it includes the timestamp.

## Removed

- `spacepackets.cfdp.conf.check_packet_length`
- `spacepackets.log` module.
- `spacepackets.ecss.tc.PusTelecommand` and `spacepackets.ecss.tm.PusTelemetry`: `valid` property
  removed. Instead, detection of an invalid CRC will now trigger a `InvalidTmCrc16` or
  `InvalidTcCrc16` exception.

## Deprecated

- Printer utilities for PUS TMTC classes.

# [v0.14.0rc2] 2022-01-30

## Fixed

- `ecss.pus_17_test.Service17Tm`: Remove (optional) PUS version argument for `unpack`
- `ccsds.time.CdsShortTimestamp`: Fix for `__add__` dunder, use integer division
  when adding microseconds to MS of day.
- `ccsds.time.CdsShortTimestamp`: Fixed bug in `read_from_raw` method
  where the retrieved CCSDS days were assigned to the UNIX seconds.

## Changed

- (breaking): `parse_space_packets`: Expects a tuple of `PacketId`s instead of raw integers now
  which are converted to integers internally.
- (breaking): `AbstractPusTm` `get_sp_header` renamed to `sp_header` and is a property now.
- (breaking): `ecss.PusTelemetry`: public member `sp_header` is now named `space_packet_header` to
  avoid name clash with new property.
- (breaking): `SequenceFlags` argument removed from `ecss.tc.PusTelecommand`. ECSS specifies this
  field is always set to `SequenceFlags.UNSEGMENTED`.

## Added

- New `ecss.PacketFieldU8`, `ecss.PacketFieldU16` and `ecss.PacketFieldU32` helper types.
- (breaking): `AbstractPusTm`: Add new `time_provider` abstract property which should return
  `Optional[CcsdsTimeProvider]`
- New `ecss.check_pus_crc` function to check whether a PUS packet in raw format.

# [v0.14.0rc1] 2022-01-22

## Changed

- `CcsdsTimeProvider`: Add `len_packed`, mark `len` as deprecated
- `ecss.pus_1_verification`:
  - `Service1Tm`: `time_provider` needs to be passed explicitely now, no default value.

## Fixes

- `ecss.tm.PusTelemetry`: Various fixes for new optional timestamp feature, added checks
  that timestamp is not None. `time_provider` does not have a default value anymore and needs
  to be passed explicitely.
- `CdsShortTimestamp`: The new `from_now` (and former `from_current_time`) classmehod now creates
  the timestamp from a UTC datetime.
- `CdsShortTimestamp`: The `datetime.datetime` instance returned from `as_date_time` now
  returns has the `datetime.timezone.utc` set as the time zone information.

## Added

- `CdsShortTimestamp`:
  - Add new `from_now` classmethod and deprecate `from_current_time`.
  - Add `__eq__` implementation which only compares CCSDS days and ms of day.

# [v0.14.0rc0] 2022-01-18

## Added

- `CdsShortTimestamp`
  - Add `__add__` magic method impl which allows adding timedeltas
    (but only timedeltas)
  - Add new constructor `from_date_time` to create timestamp from `datetime.datetime`
  - Add `ms_of_day` and `ccsds_days` properties
  - (breaking): `ms_of_day` staticmethod renamed to `ms_of_today`

## Changed

- `CcsdsTimeProvider`: Renamed `as_datetime` to `as_date_time`. Old function still there but marked
  deprecated.
- (breaking): The `CcsdsTimeProvider` is now optional for the ECSS TM packet constructors, but
  needs to be supplied explicitely. There is no automatic construction of a specific version of the
  CDS timestamp with 16 bit days anymore if no time provider is passed. If this behaviour
  is still required, `CdsShortTimestamp.empty()` can be passed explicitely. If not time provider
  is passed, it is assumed the time field is empty.
- (breaking): `PusServices` renamed to `PusService`, not a flag enum.
- (breaking): `Service17Tm.unpack`: Time reader needs to be passed explicitely as second argument.
- (breaking): Rename `pus_1_verification.Subservices` to `pus_1_verification.Subservice`
- (breaking): Rename `pus_3_hk.Subservices` to `pus_3_hk.Subservice`
- (breaking): Rename `pus_5_event.Subservices` to `pus_5_event.Subservice`
- (breaking): Rename `pus_17_test.Subservices` to `pus_17_test.Subservice`

# [v0.13.0] 2022-09-15

- Improved Time Handling inside for the TM module, make it possible
  to use different timestamps
- Introduces `CcsdsTimeProvider` abstraction to allow this.
- Improve implementation of `CdsShortTimestamp` class
- Basic `AbstractPusTm` class
- Basic `AbstractSpacePacket` class
- Singular enum names for CFPD module

# [v0.13.0rc3] 2022-07-19

- Refactored and improved TLV API and handling. Implementation is also a bit more efficient
- Basic CFDP version support: Sanity checks on version field. Only version 2 supported

# [v0.13.0rc2] 2022-07-12

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

# [v0.13.0rc1] 2022-07-01

- Update `pyproject.toml` file for full support, but still keep `setup.cfg` for now
- API improvements for PUS Verificator
- Setter properties for sequence count and APID in ECSS module
- Make `as_u32` function of `RequestId` public

# [v0.12.1] 2022-06-30

- Small bugfix for PUS 1 Step ID unpacking

# [v0.12.0] 2022-06-30

- Added `PusVerificator` module which can track the verification status of sent telecommands
- Added several magic method implementations, notably `__eq__` and `__hash__` where 
  applicable
- Removed PUS A support completely. PUS A is relatively old, and specialicing on one packet version
  makes the code a lot simpler
- Added `ecss.fields` module which contains the `Ptc` and various PFC enumerations. Also add
  a generic abstraction for enumerated fields in form of a `PacketFieldEnum` and a
  `PacketFieldBase`. This is useful to have an abstraction for the various PUS standard packet
  fields which can have variable sizes

# [v0.11.0] 2022-06-28

- Minor name change for PUS 17 and PUS 1 TM classes
- New `RequestId` class to encapsulate the field used by the PUS 1 Verification
  service
- Update CRC16 handling for TMTC PUS classes. It is possible to calculate the CRC16
  manually with a dedicated `calc_crc` call and then omit the calculation in
  the `pack` call with an additional argument.

# [v0.10.0] 2022-06-23

- New Helper objects for CCSDS Space Packet subfields, namely new
  `PacketId` and `PacketSeqCtrl` class
- Remove PUS A support for PUS telecommands
- Added multiple `__str__` and `__repr__` implementations where
  applicable
- API simplification, shorter or better keywords for PUS TM and PUS TC
  constructor calls

# [v0.9.0] 2022-06-14

- API improvements, bugfix and general improvements for CCSDS spacepacket
  header implementation

# [v0.8.1] 2022-05-24

- Named value for fetching global APID

# [v0.8.0] 2022-05-24

- Update `PusServices` enumeration

# [v0.7.1] 2022-05-05

- Added subservice enumerations for generic PUS Services 1, 3, 5 and 17

# [v0.7.0] 2022-05-05

- Improvement for API of PUS TM1 and PUS TM17 base classes

# [v0.6.2] 2022-04-08

- Fix in size pre-check of space packet parser `parse_space_packets`

# [v0.6.1] 2022-04-08

- Add packet sizes in `__str__` method of PUS TM and TC
- Some type corrections: Expect `bytes` instead of `bytearray` where applicable

# [v0.6.0] 2022-02-12

## Added

- Unified Space Data Link Protocol Packet implementations

## Changed

- Assign default print format in TM and TC implementation

# [v0.5.4] 2022-01-13

- Important bugfix in space packet parser implementation

# [v0.5.3] 2021-12-20

- Maximum TC packet size configurable now, will be checked when packaging TC packets.
  Default maximum size is 1004 bytes for now

# [v0.5.2] 2021-12-20

- Smaller tweaks for CFDP

# [v0.5.1] 2021-12-07

- Applied formatting with the `black` Python formatter
- Small tweaks to the NOTICE file
