Change Log
=======

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

# [unreleased]

# [v0.31.0] 2025-09-10

## Added

- Added back PUS-A support for both TCs and TMs
- Make CRC calculation for ECSS PUS-C `unpack` classmethods optional by adding a
  and `unpack_generic` classmethods which allows disabling the checksum validity check
- `spacepackets.ecss.peek_pus_packet_info` to peek the PUS version and SP header from a raw
  packet
- Added support for ECSS TM and ECSS TC modules for no-checksum packets via the `has_checksum`,
  `verify_checksum` constructor fields or managed parameters.
- `ManagedParams` dataclass inside the `ecss.tm` module which needs to be passed to the
  generic `unapck_generic` constructor.

## Changed

- Introduced `MiscParams` inside the `ecss.tm` module, which replaces and wraps the
  `spacecraft_time_ref` and `packet_version` parameters.
- `ecss.pus_1_verification.UnpackParams` renamed to `VerificationManagedParams`

# [v0.30.1] 2025-07-11

## Changed

- Migrated from `crc` dependency to `fastcrc` to avoid massive performance on checksum calculations,
  for example for ECSS TM/TC or for CFDP packet handling. See [#118](https://github.com/us-irs/spacepackets-py/issues/118).

# [v0.30.0] 2025-06-23

## Added

- Various missing `__hash__` impelementations.
  [113](https://github.com/us-irs/spacepackets-py/pull/113)
- EOF PDU constructor can now accept the CRC32 checksum in integer format as well.
  [114](https://github.com/us-irs/spacepackets-py/pull/114/files)

## Changed

- Replaced `crcmod` dependency by `crc` for checksum calculation
  [112](https://github.com/us-irs/spacepackets-py/pull/112)

# [v0.29.0] 2025-05-23

## Added

- CCSDS TM Frame impelementation.
  [109](https://github.com/us-irs/spacepackets-py/pull/109)

## Fixed

- Bugfix for USLP VCF count handling.
  [107](https://github.com/us-irs/spacepackets-py/pull/107)

# [v0.28.0] 2025-02-10

## Changed

- Improved the space packet parser API: The `parse_space_packets` function simply expects
  a byte buffer and returns results and useful context information inside a `ParseResult`
  structure. The former `parse_space_packets` was renamed to `parse_space_packets_from_deque`
  and now treats the provided `deque` read-only.

# [v0.27.0] 2025-01-15

## Changed

- USLP implementation: FECF is fixed to 2 bytes and always uses the standard CRC16 CCITT checksum
  calculation now. Consequently, the USLP API was adapted and simplified.
  - `FecfProperties` removed, not required anymore
  - `TransferFrame` constructor now expects `has_fecf` boolean parameter which defaults to true.
     The checksum will be calculated and appended by the `pack` method. The `unpack` method
     expects the `has_fecf` flag now as well and will perform a CRC16 calculation when the flag
     is set to True.

# [v0.26.1] 2024-11-30

## Fixed

- Unpacking / re-packing was buggy for some file directives when the PDU checksum was activated.
  This was fixed for the following PDUs:
  - NAK
  - EOF
  - File Data
  - Metadata
  - Finished

## Added

- Typing improvements: Most raw byte APIs like `unpack` methods now accept both `bytes` and
  `bytearray`

# [v0.26.0] 2024-11-27

- Python 3.8 is not supported anymore as it has reached end-of-life.

## Changed

- `MetadataPdu` options have to be specified as an optional list of abstract TLVs now.
   A new getter method `options_as_tlv` can be used to retrieve a list of concrete TLV objects.
- All exceptions has an `*Error` suffix now
- Removed `exceptions` module in CFDP and moved it to individual `defs` definition modules.
  The Errors can still be directly imported from `spacepackets.cfdp` or `spacepackets.cfdp.tlv`.

## Fixed

- `CrcError` exception constructor was previously named `__int__` by accident.

# [v0.25.0] 2024-10-29

## Changed

Renamed `PusFileSeqCountProvider` to `CcsdsFileSeqCountProvider` but keep old alias.

## Added

- New `SpacePacketHeader.tc` and `SpacePacketHeader.tm` constructors which set the packet
  type correctly

# [v0.24.2] 2024-10-15

## Fixed

- Custom `EntityIdTlv` `__eq__` implementation which only compares the numerical value
  of the entity ID TLVs

## Added

- `AbstractTlvBase` `__repr__` implementation

# [v0.24.1] 2024-04-23

## Reverted

- The `apid` constructor arguments for the PUS TMTC constructors now have a default value of 0.
  This allows setting the APID in a centralized manner for APID groups and can reduce duplication.

# [v0.24.0] 2024-04-23

## Removed

- Global configuration module for TC and TM APID was removed.

## Changed

- ECSS PUS telemetry time handling is now more generic and low level: Constructors expect
  a simple `bytes` type while unpackers/readers expect the length of the timestamp. A helper
  constant for the offset of the timestamp is exposed which can help with determining the
  length of the timestamp.
- `CdsShortTimestamp.from_now` renamed to `now`.
- The ECSS TMTC APID field must not be set explicitely in the class constructors.

## Added

- `spacepackets.ecss.tm.PUS_TM_TIMESTAMP_OFFSET` constant which can be used as a look-ahead to
  determine the timestamp length from a raw PUS TM packet.
- `spacepackets.ccsds.CCSDS_HEADER_LEN` constant.

# [v0.23.1] 2024-04-22

## Added

- PUS TC app data setter method.
- New `PusTelecommand` alias/shorthand: `PusTc`.
- New `SpacePacketHeader` alias/shorthand: `SpHeader`.
- New `PusTelemetry` alias/shorthand: `PusTm`.

# [v0.23.0] 2024-01-24

## Changed

- Explicitely disambigute `ByteFieldU<[8, 16, 32, 64]>.from_bytes` from
  `UnsignedByteField.from_bytes` by renaming them to
  `ByteFieldU<[8, 16, 32, 64].from_<[8, 16, 32, 64]>_bytes`. This might break calling code which
  might now call `UnsignedByteField.from_bytes`.
- Improve `ByteFieldGenerator.from_int` and `ByteFieldGenerator.from_bytes` method. These
  will now raise an exception if the passed value width in not in [1, 2, 4, 8].

## Added

- Added `ByteFieldU64` variant.
- Added `spacepackets.countdown` utility module. This class was moved from
  `tmtccmd.util.countdown` and contains the `Countdown` class. It was moved here so it can
  be re-used more easily.
- Added `spacepackets.seqcount` utility module. This class was moved from
  `tmtccmd.util.seqcnt` and contains sequence counter abstractions and concrete implementations.
  It was moved here so it can be re-used more easily.

# [v0.22.0] 2023-12-22

## Changed

- Extended `AbstractSpacePacket` with the following abstract properties:
  - `ccsds_version`
  - `packet_id`
  - `packet_seq_control`
  - The following properties were added but use the abstract properties:
    - `packet_type`
    - `sec_header_flag`
    - `seq_flags`

## Fixed

- Metadata PDU typing correction.
- More robust `__eq__` implementations which check the type compared against.
- Some minor typing corrections.

## Added

- The `PusTelecommand` class now implements `AbstractSpacePacket`.

# [v0.21.0] 2023-11-10

## Fixed

- Directive code for the NAK PDU was set to the ACK PDU directive code.

## Changed

- Reordered argument order for `FinishedParams` to be in line with the CFDP standard. This might
  break code not using keyword arguments.
- Renamed `FileDeliveryStatus` to `FileStatus` to be closer to the CFDP name.
- Moved `spacepackets.cfdp.pdu.finished.FileDeliveryStatus` to `spacepackets.cfdp.defs.FileStatus`.
  The new enumeration is also re-exported in `spacepackets.cfdp`.
- Moved `spacepackets.cfdp.pdu.finished.DeliveryCode` to `spacepackets.cfdp.defs.DeliveryCode`.
  The new enumeration is also re-exported in `spacepackets.cfdp`.
- Renamed `len` field of CFDP LV to `value_len` to avoid confusion and for consistency.
- Renamed `length` field of CFDP TLV to `value_len` to avoid confusion and for consistency.

## Added

- New `TransactionId` class used for unique identification of CFDP transfers.
- `UnsignedByteField.from_bytes` constructor.
- `DirectoryOperationMessageType` enumeration for CFDP.
- `OriginatingTransactionId` reserved CFDP message abstraction.
- `ProxyPutResponse` reserved CFDP message abstraction.
- `ProxyTransmissionMode` reserved CFDP message abstraction.
- `ProxyClosureRequested` reserved CFDP message abstraction.
- `DirectoryListingRequest` reserved CFDP message abstraction.
- `DirectoryListingResponse` reserved CFDP message abstraction.

## Removed

- USLP configuration module.

# [v0.20.0] 2023-11-04

## Added

- Added `__repr__` for `AckPdu` class.
- Added `__repr__` for `KeepAlivePdu` class.
- Added `__repr__` for `PromptPdu` class.
- Added a `finished_params` property for the `FinishedPdu` class.
- Added a `transmission_mode` property for the `AbstractPduBase` class.
- Renamed `trans_mode` setter and getter properties to `transmission_mode`.
- Filedata PDU: New `SegmentMetadata` dataclass for better modelling of the filedata PDU.
- Filedata PDU: New API to retrieve the maximum allowed file segment size for a given maximum
  packet size.
- NAK PDU: New API to retrieve the maximum amount of segment requests for a given maximum packet
  size.

## Changed

- Filedata PDU: The `FileDataParams` dataclass now is composed of an `Optional[SegmentMetadata]`.

# [v0.19.0] 2023-10-05

## Fixed

- Set the `direction` field of the PDU classes correctly depending on the PDU type. This field
  was previously always set to `Direction.TOWARDS_RECEIVER`.

## Changed

- Moved `pdu_header` abstract property from `AbstractFileDirectiveBase` to `AbstractPduBase`
  class
- Renamed `TlvHolder` field `base` to `tlv` and `PduHolder` field `base` to `pdu`.

## Added

- Added `direction` abstract method for `AbstractPduBase`.

# [v0.18.0] 2023-09-08

## Changed

- The `parse_space_packets` function analysis queue argument is now expected to be filled
  on the right side.

# [v0.18.0rc1] 2023-09-04

## Added

- New `ProxyPutRequestParams` dataclass as a generic data model for the CFDP proxy put request
  parameters.
- New API for `ReservedCfdpMessage`
  - `get_reserved_cfdp_message_type`: Retrieve type as `int`
  - `is_cfdp_proxy_operation`
  - `get_cfdp_proxy_message_type`
  - `get_proxy_put_request_params` to extract proxy put request parameters
    from the message when applicable.
- `MessageToUserTlv`: Added new method `to_reserved_msg_tlv` which can be used to create
  a `ReservedCfdpMessage` from the instance when applicable.

## Changed

- Renamed `MessageToUserTlv.is_standard_proxy_dir_ops_msg` to `is_reserved_cfdp_message`
- `ProxyPutRequest` constructor now expects a `ProxyPutRequestParams` instance.
- Swapped `FileDataPdu`, `KeepAlivePdu`, `EofPdu`, `FinishedPdu`, `PromptPdu` and `AckPdu`
  constructor argument order : `PduConfig` is the first parameter now while
  `FileDataParams` is the second parameter. `PduConfig` is the only common parameter, so it makes
  more sense to have it as the first argument.

## Fixed

- The new `is_reserved_cfdp_message` API now checks for a value length of 5 to ensure the message
  type is included as well.

# [v0.18.0rc0] 2023-08-17

- Bumped required Python version to v3.8.

## Changed

- Renamed `TlvTypes` to `TlvType`.
- Package version is single-sourced using the `importlib.metadata` variant: The `pyproject.toml`
  now contains the version information, but the informatio can be retrieved at runtime
  by using the new `version.get_version` API or `importlib.metadata.version("spacepackets")`.

## Added

- Added basic low level support for the Proxy Put Request operation.

## Removed

- `setup.py` which is not required anymore.

# [v0.17.0] 2023-06-09

## Changed

- Moved `CRC16_CCITT_FUNC` from `spacepackets.ecss.crc` to `spacepackets.crc`. This checksum is
  not just used by PUS, but by the CCSDS TC and the CFDP standard as well.

## Added

- Checksum and PDU length checks when creating PDUs from a raw buffer.
- CRC flag support for CFDP.

## Fixed

- Bugfix in `ccsds.spacepackets` `parse_space_packets` function: If a broken
  packet was detected and the current parsing index was larger than 0, the broken
  packet was not detected and re-inserted into the `deque` properly.

# [v0.16.0] 2023-05-15

## Fixed

- Important bugfix in CFDP PDU header format: The entity length field and the transaction sequence
  number length field stored the actual length of the field instead of the length minus 1 like
  specified in the CFDP standard.

# [v0.15.0] 2023-02-17

- Removed `ecss.pus_5_event.Severity`, moved to `tmtccmd` package because it is not ECSS generic.
- Added first basic `ecss.pus_15_tm_storage` module with `Subservice` enum.

# [v0.14.1] 2023-02-12

## Changed

- Use custom package discovery in `pyproject.toml` for more robustness.

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

[unreleased]: https://github.com/us-irs/spacepackets-py/compare/v0.31.0...HEAD
[v0.31.0]: https://github.com/us-irs/spacepackets-py/compare/v0.30.1...v0.31.0
[v0.30.1]: https://github.com/us-irs/spacepackets-py/compare/v0.30.0...v0.30.1
[v0.30.0]: https://github.com/us-irs/spacepackets-py/compare/v0.29.0...v0.30.0
[v0.29.0]: https://github.com/us-irs/spacepackets-py/compare/v0.28.0...v0.29.0
[v0.28.0]: https://github.com/us-irs/spacepackets-py/compare/v0.27.0...v0.28.0
