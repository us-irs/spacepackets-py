cfdp.pdu package
===============================

The Protocol Data Unit (PDU) subpackage contains the CFDP data units
which can be used by CFDP entities to exchange file data.

In general, PDUs are divided in File Directive PDUs and File Data PDUs.

Following File Directive PDUs are available in the subpackage

- ACK: :py:mod:`spacepackets.cfdp.pdu.ack`
- NAK: :py:mod:`spacepackets.cfdp.pdu.nak`
- Finished: :py:mod:`spacepackets.cfdp.pdu.finished`
- Metadata: :py:mod:`spacepackets.cfdp.pdu.metadata`
- EOF: :py:mod:`spacepackets.cfdp.pdu.eof`
- Keep Alive: :py:mod:`spacepackets.cfdp.pdu.keep_alive`

All are based on the :py:mod:`spacepackets.cfdp.pdu.file_directive`
module.

Following File Data PDUs are available in the subpackage

- File Data: :py:mod:`spacepackets.cfdp.pdu.file_data`
 
Every PDU type has a common PDU header which can be found inside the
:py:mod:`spacepackets.cfdp.pdu.header` module.

The helper module :py:mod:`spacepackets.cfdp.pdu.helper` contains components like the
:py:class:`spacepackets.cfdp.pdu.helper.PduWrapper` class which stores PDUs as a generic base type
and allows typed conversion in to the concrete PDU type

spacepackets.cfdp.pdu.helper module
-----------------------------------------

.. automodule:: spacepackets.cfdp.pdu.helper
   :members:
   :undoc-members:
   :show-inheritance:

File Data Submodules
------------------------

spacepackets.cfdp.pdu.file_data module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: spacepackets.cfdp.pdu.file_data
   :members:
   :undoc-members:
   :show-inheritance:

File Directive Submodules
------------------------------

spacepackets.cfdp.pdu.ack module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: spacepackets.cfdp.pdu.ack
   :members:
   :undoc-members:
   :show-inheritance:

spacepackets.cfdp.pdu.nak module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: spacepackets.cfdp.pdu.nak
   :members:
   :undoc-members:
   :show-inheritance:

spacepackets.cfdp.pdu.eof module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: spacepackets.cfdp.pdu.eof
   :members:
   :undoc-members:
   :show-inheritance:

spacepackets.cfdp.pdu.keep_alive module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: spacepackets.cfdp.pdu.keep_alive
   :members:
   :undoc-members:
   :show-inheritance:

spacepackets.cfdp.pdu.metadata module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: spacepackets.cfdp.pdu.metadata
   :members:
   :undoc-members:
   :show-inheritance:

spacepackets.cfdp.pdu.finished module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: spacepackets.cfdp.pdu.finished
   :members:
   :undoc-members:
   :show-inheritance:

spacepackets.cfdp.pdu.header module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: spacepackets.cfdp.pdu.header
   :members:
   :undoc-members:
   :show-inheritance:

spacepackets.cfdp.pdu.file_directive module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: spacepackets.cfdp.pdu.file_directive
   :members:
   :undoc-members:
   :show-inheritance:

