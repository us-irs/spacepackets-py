Packet Overview
===================

CCSDS Space Packet Standard
-----------------------------

Extended information can be found in `CCSDS 727.0-B-5`_.
A space packet consists of a packet primary header and a packet data field.
The packet data field consists of a packet secondary header and a user data field.
PUS packets are a type of space packets and have been explained in great detail in
the chapter below. You can also find a concrete example of a Space Packet in form
of a ping telecommand there.

ECSS Packet Utilisation Standard (PUS)
---------------------------------------

All packet 16-bit checksums for Telecommands (TCs) and Telemetry (TMs) are
calculated with CRC-CCITT. In Python, the pre-defined ``crc-ccitt-false``
function from the `crcmod package`_  can be used to calculate this checksum.

Telecommands
^^^^^^^^^^^^^^^^^^

This chapter contains some high level information about the
:py:class:`spacepackets.ecss.tc.PusTelecommand` class. Extended information can be found
in `ECSS-E-70-41A`_  on p.42 or in `ECSS-ST-E-70-41C`_ starting at page 442.

The structure is shown as follows for a ping telecommand using the PUS service 17 with the
subervice ID 1. This can also be denoted more briefly as TC[17,1]. The first part
of the packet is always the the Space Packet Header because PUS packets are a subtype of space
packets. The packet length is an unsigned integer C = Number of Octets in Packet Data Field - 1.
The example below has a source sequence count of 25 and an APID of 0x73.

.. code-block::

     o = optional, Srv = Service
       ------------------------------------------------------------------------------------------------------------------
     / ------------------------------------------Packet Header(48)------------------------------------------ |   Packet  \
     |----------------Packet ID(16)-----------------------|Packet Sequence Control (16) | Packet Length (16)| Data Field |
     |Version       | Type(1) |Data Field    |APID(11)    | SequenceFlags(2) |Sequence |                    | (Variable) |
     |Number(3)     |         |Header Flag(1)|            |                  |Count(14)|                    |            |
    h|          0x18               |    0x73              |       0xc0       | 0x19    |   0x00  |   0x04   |            |
    b|   000      1      1      000|  01110011            | 11  000000       | 00011001|00000000 | 0000100  |            |
    d|    0   |   1   |  1     |    115(ASCII s)          | 3 |            25          |   0     |    4     |            |
      ---------------------------------------------------------------------------------------------------------------------

The second part is the packet data field which also includes a PUS data field header.

PUS C
""""""

.. code-block::

     o = optional, Srv = Service
       -------------------------------------------------------------------------------------------------------
     / -----------------------------------------------Packet Data Field--------------------------------------- \
     | --------------------------------Data Field Header ------------------ | --------User Data Field--------- |
     |TC PUS Ver.(4)|Ack(4)|SrvType (8)|SrvSubtype(8)|Source ID(16)|Spare(o)|AppData|Spare(o)|PacketErrCtr (16)|
    h|        0x2F         |    0x11   |   0x01      | 0x00 | 0x00 |        |       |        | 0xA0  |  0xB8   |
    b| 0010       1111     |  00010001 | 00000001    | 0..0 | 0..0 |        |       |        |       |         |
    d|   2          15     |    17     |     1       |  0   |  0   |        |       |        |       |         |
      ----------------------------------------------------------------------------------------------------------

PUS A
""""""

PUS A is not supported anymore starting at version ``v0.12.0``.

.. code-block::

     o = optional, Srv = Service
       -----------------------------------------------------------------------------------------------------------------
     / -----------------------------------------------Packet Data Field------------------------------------------------- \
     | --------------------------------Data Field Header ---------------------------|AppData|Spare|    PacketErrCtr      |
     |CCSDS(1)|TC PUS Ver.(3)|Ack(4)|SrvType (8)|SrvSubtype(8)|Source ID(o)|Spare(o)|  (var)|(var)|         (16)         |
    h|       0x11 (0x1F)            |  0x11     |   0x01      |            |        |       |     | 0xA0     |    0xB8   |
    b|   0     001     1111         |00010001   | 00000001    |            |        |       |     |          |           |
    d|   0      1       1111        |    17     |     1       |            |        |       |     |          |           |
      --------------------------------------------------------------------------------------------------------------------

Telemetry
^^^^^^^^^^^^

This chapter contains some high level information about the
:py:class:`spacepackets.ecss.tm.PusTelemetry` class. Extended information can be found
in `ECSS-E-70-41A`_  on p.42 or in `ECSS-ST-E-70-41C`_ starting at page 442.

The structure is shown as follows for a ping reply using the PUS service 17 with the
subervice ID 2. This can also be denoted more briefly as TM[17,2]. The first part
of the packet is always the the Space Packet Header because PUS packets are a subtype of space
packets. The packet length is an unsigned integer C = Number of Octets in Packet Data Field - 1.

.. code-block::

       ------------------------------------------------------------------------------------------------------------------
     / ------------------------------------------Packet Header(48)------------------------------------------ |   Packet   \
     | ---------------Packet ID(16)----------------------- | Packet Sequence Control (16)| Packet Length (16)| Data Field |
     |   Version      | Type(1) |Data Field    |APID(11)   | SequenceFlags(2) |Sequence  |                   | (Variable) |
     |  Number(3)     |         |Header Flag(1)|           |                  |Count(14) |                   |            |
    h|           0x08               |    0x73              |       0xc0       | 0x19     |   0x00  |   0x04  |            |
    b|    000      0      1      000|  01110011            | 11  000000       | 00011001 |00000000 | 0000100 |            |
    d|     0   |   0   |  1     |    115(ASCII s)          | 3 |            25           |   0     |    4    |            |
      ---------------------------------------------------------------------------------------------------------------------

The second part is the packet data field which also includes a PUS data field header.

PUS C
""""""

.. code-block::

      ---------------------------------------------------------------------------------------------------------------------
     /------------------------------------------------Packet Data Field---------------------------------------------------- \
     |---------------------------------Data Field Header -------------------------------------------- | --User Data Field-- |
     |TM PUS Ver.(4)|TimeRef(4)|SrvType (8)|SrvSubtype(8)|Subcounter(16)|DestId(16)|Time(var)|Spare(o)|Data|Spare| CRC(16)  |
    h|          0x20           |  0x11     |   0x02      | 0x00 | 0x00  |0x00|0x00 |         |        |    |     |   Calc.  |
    b|    0010     0000        |00010001   | 00000010    | 0..0 | 0..0  |0..0|0..0 |         |        |    |     |   Calc.  |
    d|     2         0         |    17     |     2       |      0       |     0    |         |        |    |     |   Calc.  |
      ----------------------------------------------------------------------------------------------------------------------

PUS A
""""""

PUS A is not supported anymore starting at version ``v0.12.0``.

.. code-block::

      ---------------------------------------------------------------------------------------------------------------------
     /------------------------------------------------Packet Data Field--------------------------------------------------- \
     |---------------------------------Data Field Header ---------------------------------------|AppData|Spare|PacketErrCt |
     |Spare(1)|TM PUS Ver.(3)|Spare(4)|SrvType(8)|SrvSubtype(8)|Subcounter(8,o)|Time(var)|Spare(o)|(var)  |(var)|  (16)    |
    h|        0x11 (0x1F)             |  0x11    |   0x02      |  0x00         |         |        |       |     |   Calc.  |
    b|    0     001     0000          |00010001  | 00000010    |    0..0       |         |        |       |     |          |
    d|    0      1       0            |    17    |     2       |       0       |         |        |       |     |          |
      ----------------------------------------------------------------------------------------------------------------------

.. _`CCSDS 727.0-B-5`: https://public.ccsds.org/Pubs/727x0b5.pdf
.. _`ECSS-E-70-41A`: https://ecss.nl/standard/ecss-e-70-41a-ground-systems-and-operations-telemetry-and-telecommand-packet-utilization/
.. _`ECSS-ST-E-70-41C`: https://ecss.nl/standard/ecss-e-st-70-41c-space-engineering-telemetry-and-telecommand-packet-utilization-15-april-2016/
.. _`crcmod package`: http://crcmod.sourceforge.net/crcmod.predefined.html