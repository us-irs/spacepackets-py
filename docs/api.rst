API Documentation
===================

This package is split into three subpackages:

- ``ccsds``: Contains CCSDS specific code. This includes the space packet implementation
  inside the ``spacepacket`` module and time related implementations in the ``time`` module

- ``cfdp``: Contains packet implementations related to the CCSDS File Delivery Protocol
- ``ecss``: Contains packet implementations related to the ECSS PUS standard. This includes
  TM implementations in the ``tm`` module and TC implementations inside the ``tc`` module

To avoid specifying packet configuration which generally stays the same repeatedly, some parameters
can also be set via ``conf`` modules inside each subpackage.

The ``spacepacket`` package also uses the ``logging`` package to emmit warnings. The user
can use the ``log`` module of the package to specify a custom logger name.

.. toctree::
   :maxdepth: 4

   api/ccsds
   api/ecss_tc
   api/ecss_tm
   api/ecss
   api/cfdp
   api/cfdp_pdu

spacepackets.log module
-------------------------

.. automodule:: spacepackets.log
   :members:
   :undoc-members:
   :show-inheritance:

spacepackets.util module
--------------------------

.. automodule:: spacepackets.util
   :members:
   :undoc-members:
   :show-inheritance: