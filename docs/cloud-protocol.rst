G90 Alarm Panel: cloud protocol
=============================================

.. contents::

Version
-------

The cloud protocol version: 1.1 (presumably, as seen in response to ``GETHOSTINFO`` local command).

Description
-----------

The cloud protocol is TCP based, using ``47.88.7.61`` as destination IP address and port ``5678`` (both as seen towards cloud service side)

The protocol is binary with header and command-specific payload. See below for requests and responses wire format.

Security
--------

.. warning:: The cloud protocol *does not* provide any authorization or encryption. Presumably, the device ID (GUID) is what identifies the panel to the cloud service.

Packet format
-------------
TBD

Header format
-------------
TBD

Payload format
--------------
TBD