Packet Overview
===================

ECSS Packet Utilisation Standard (PUS)
---------------------------------------

Telecommands
^^^^^^^^^^^^^^^^^^

Extended information can be found in ECSS-E-70-41A  on p.42 or in ECSS-ST-E-70-41C starting at
page 442.


The structure is shown as follows for a TC[17,1] example.
The first part is always the the Space Packet Header because PUS packets are a
subtype of space packets

.. code-block::

    o = optional, Srv = Service
    |-------------------------------------------Packet Header(48)------------------------------------------|   Packet   |
    |----------------Packet ID(16)-----------------------|Packet Sequence Control (16) | Packet Length (16)| Data Field |
    |Version       | Type(1) |Data Field    |APID(11)    | SequenceFlags(2) |Sequence |                    | (Variable) |
    |Number(3)     |         |Header Flag(1)|            |                  |Count(14)|                    |            |
    |          0x18               |    0x73              |       0xc0       | 0x19    |   0x00  |   0x04   |            |
    |   000      1      1      000|  01110011            | 11  000000       | 00011001|00000000 | 0000100  |            |
    |    0   |   1   |  1     |    115(ASCII s)          | 3 |            25          |   0     |    4     |            |

The second part is the packet data field which also includes a PUS data field header.

PUS A
""""""

.. code-block::

    o = optional, Srv = Service
    | -----------------------------------------------Packet Data Field------------------------------------------------- |
    | --------------------------------Data Field Header ---------------------------|AppData|Spare|    PacketErrCtr      |
    |CCSDS(1)|TC PUS Ver.(3)|Ack(4)|SrvType (8)|SrvSubtype(8)|Source ID(o)|Spare(o)|  (var)|(var)|         (16)         |
    |       0x11 (0x1F)            |  0x11     |   0x01      |            |        |       |     | 0xA0     |    0xB8   |
    |   0     001     1111         |00010001   | 00000001    |            |        |       |     |          |           |
    |   0      1       1111        |    17     |     1       |            |        |       |     |          |           |

PUS C
""""""

.. code-block::

    o = optional, Srv = Service
    | -----------------------------------------------Packet Data Field--------------------------------------- |
    | --------------------------------Data Field Header ------------------ | --------User Data Field--------- |
    |TC PUS Ver.(4)|Ack(4)|SrvType (8)|SrvSubtype(8)|Source ID(16)|Spare(o)|AppData|Spare(o)|PacketErrCtr (16)|
    | 0x11 (0x1F)         |    0x11   |   0x01      | 0x00 | 0x00 |        |       |        | 0xA0  |  0xB8   |
    | 0010       1111     |  00010001 | 00000001    | 0x00 | 0x00 |        |       |        |       |         |
    | 0010       1111     |    17     |     1       | 0x00 | 0x00 |        |       |        |       |         |
