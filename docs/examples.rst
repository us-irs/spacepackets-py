Examples
=========

You can find all examples listed here in the ``example`` `folder <https://github.com/robamu-org/py-spacepackets/tree/main/examples>`_
of the project as well.

ECSS PUS packets
-----------------

The following example shows how to generate PUS packets using the PUS ping telecommand and a
PUS ping telemetry reply.

.. testsetup:: pus

    from spacepackets.ecss.tc import PusTelecommand
    from spacepackets.ecss.tm import PusTelemetry

.. testcode::  pus

    ping_cmd = PusTelecommand(service=17, subservice=1, apid=0x01)
    cmd_as_bytes = ping_cmd.pack()
    print(f"Ping telecommand [17,1] (hex): [{cmd_as_bytes.hex(sep=',')}]")

    ping_reply = PusTelemetry(service=17, subservice=2, apid=0x01)
    tm_as_bytes = ping_reply.pack()
    print(f"Ping reply [17,2] (hex): [{tm_as_bytes.hex(sep=',')}]")

CCSDS Space Packet
-------------------

`This CCSDS example <https://github.com/robamu-org/py-spacepackets/blob/main/examples/example_spacepacket.py>`_
shows how to generate a space packet header:

USLP Frames
-------------------

`This USLP example <https://github.com/robamu-org/py-spacepackets/blob/main/examples/example_uslp.py>`_
shows how to generate a simple variable length USLP frame containing a simple space packet
ample shows how to generate a generic CCSDS Space Packet Header
