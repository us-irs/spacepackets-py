API Documentation
===================

This package is split into three subpackages:

- :py:mod:`spacepackets.ccsds`: Contains CCSDS specific code. This includes the space packet
  implementation inside the :py:mod:`spacepackets.ccsds.spacepacket` module and time related
  implementations in the :py:mod:`spacepackets.ccsds.time` module

- :py:mod:`spacepackets.cfdp`: Contains packet implementations related to the CCSDS File Delivery Protocol
- :py:mod:`spacepackets.ecss`: Contains packet implementations related to the ECSS PUS standard.

To avoid specifying packet configuration which generally stays the same repeatedly, some parameters
can also be set via ``conf`` modules inside each subpackage.

This package also uses the :py:mod:`logging` package to emit warnings.

.. toctree::
   :maxdepth: 3

   api/exceptions
   api/ccsds
   api/ccsds_time
   api/ecss_tc
   api/ecss_tm
   api/ecss
   api/cfdp
   api/cfdp_pdu
   api/util
