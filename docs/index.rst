.. dle-encoder documentation master file, created by
   sphinx-quickstart on Tue Aug 17 11:27:40 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

ECSS and CCSDS Spacepackets
=======================================

This package contains generic implementations for various CCSDS
(Consultative Committee for Space Data Systems) and ECSS
(European Cooperation for Space Standardization) packet standards.

Currently, this includes the following components:

- Space Packet implementation according to `CCSDS Blue Book 133.0-B-2`_.
- CCSDS CDS short timestamp implementation according to `CCSDS 301.0-B-4 3.3`_.
- PUS Telecommand and PUS Telemetry implementation according to the
  `ECSS-E-ST-70-41C standard`_.
- CCSDS File Delivery Protcol (CFDP) packet implementations according to
  `CCSDS Blue Book 727.0-B-5`_.
- Unified Space Data Link Protocol (USLP) frame implementations according to
  `CCSDS Blue Book 732.1-B-2`_ .

It also contains various helper modules

- :py:class:`spacepackets.ecss.pus_verificator.PusVerificator` class to track the verification of sent telecommands
- PTC and PFC definitions for ECSS packets inside the :py:mod:`spacepackets.ecss.fields` module

Other pages (online)
---------------------

- `project page on GitHub`_
- This page, when viewed online is at https://spacepackets.readthedocs.io/en/latest

.. toctree::
   :maxdepth: 2
   :caption: Contents:

.. _`project page on GitHub`: https://github.com/robamu-org/py-spacepackets
.. _`CCSDS Blue Book 133.0-B-2`: https://public.ccsds.org/Pubs/133x0b2e1.pdf
.. _`ECSS-E-ST-70-41C standard`: https://ecss.nl/standard/ecss-e-st-70-41c-space-engineering-telemetry-and-telecommand-packet-utilization-15-april-2016/
.. _`CCSDS Blue Book 727.0-B-5`: https://public.ccsds.org/Pubs/727x0b5.pdf
.. _`CCSDS Blue Book 732.1-B-2`: https://public.ccsds.org/Pubs/732x1b2.pdf
.. _`CCSDS 301.0-B-4 3.3`: https://public.ccsds.org/Pubs/301x0b4e1.pdf

.. toctree::
   :maxdepth: 4

   examples
   packets
   api



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
