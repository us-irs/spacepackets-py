Examples
=========

You can find all examples listed here in the ``example`` folder of the project as well.

ECSS PUS packets
-----------------

This examples shows how to generate PUS packets using the PUS ping telecommand and a PUS
ping telemetry reply.

.. code-block::

   from spacepackets.ecss.tc import PusTelecommand
   from spacepackets.ecss.tm import PusTelemetry
   from spacepackets.util import get_printable_data_string, PrintFormats

   def main():
       ping_cmd = PusTelecommand(
           service=17,
           subservice=1,
           apid=0x01
       )
       cmd_as_bytes = ping_cmd.pack()
       print_string = get_printable_data_string(print_format=PrintFormats.HEX, data=cmd_as_bytes)
       print(f'Ping telecommand [17,1]: {print_string}')

       ping_reply = PusTelemetry(
           service=17,
           subservice=2,
           apid=0x01
       )
       tm_as_bytes = ping_reply.pack()
       print_string = get_printable_data_string(print_format=PrintFormats.HEX, data=tm_as_bytes)
       print(f'Ping reply [17,2]: {print_string}')


   if __name__ == "__main__":
       main()


CCSDS Space Packet
-------------------

This example shows how to generate a generic CCSDS Space Packet Header

.. code-block::

   from spacepackets.ccsds.spacepacket import SpacePacketHeader, PacketTypes
   from spacepackets.util import get_printable_data_string, PrintFormats


   def main():
       spacepacket_header = SpacePacketHeader(
           packet_type=PacketTypes.TC,
           apid=0x01,
           source_sequence_count=0,
           data_length=0
       )
       header_as_bytes = spacepacket_header.pack()
       print_string = get_printable_data_string(print_format=PrintFormats.HEX, data=header_as_bytes)
       print(f'Space packet header: {print_string}')


   if __name__ == "__main__":
       main()
