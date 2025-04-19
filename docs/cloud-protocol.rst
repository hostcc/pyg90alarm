G90 Alarm Panel: cloud protocol
=============================================

.. contents::

Version
-------

The cloud protocol version: 1.1 (presumably, as seen in response to ``GETHOSTINFO`` local command).

Description
-----------

The cloud protocol is TCP based, using ``47.88.7.61`` as destination IP address and port ``5678`` (both as seen towards cloud service side). The connection is always initiated by the alarm panel.

The protocol is binary with header (basic or versioned) and command-specific payload. All data is sent in host order (little-endian, LSB first). See below for their wire format.

Security
--------

.. warning:: The cloud protocol *does not* provide any authorization or encryption. Presumably, the device ID (GUID) is what identifies the panel to the cloud service.

Packet format
-------------

The G90 cloud protocol packets consist of a header followed by command-specific payload:

::

    +----------------+------------------------+
    |     Header     |        Payload         |
    | (8 or 12 bytes)|  (variable length)     |
    +----------------+------------------------+

Header format
-------------

The protocol uses two types of headers:

1. Basic Header (8 bytes):

::

    0                   1                   2                   3
    0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |    Command    |     Source    |     Flag1     | Destination   |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                       Message Length                          |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

2. Versioned Header (12 bytes):

::

    0                   1                   2                   3
    0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |    Command    |     Source    |     Flag1     | Destination   |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                       Message Length                          |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |            Version            |           Sequence            |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

Where:

- **Command**: The command type (see `G90CloudCommand <../../src/pyg90alarm/cloud/const.py>`_)
- **Source**: The source direction of the message (see `G90CloudDirection <../../src/pyg90alarm/cloud/const.py>`_)
- **Flag1**: A flag of unknown purpose (typically 0x00)
- **Destination**: The destination direction of the message (see `G90CloudDirection <../../src/pyg90alarm/cloud/const.py>`_)
- **Message Length**: Total length of the message including header and payload
- **Version**: Protocol version (0x01 for protocol version 1.1)
- **Sequence**: Sequence number, either 0 for single message in the packet or starting from 1 for multiple ones

Payload format
--------------

The payload format is command-specific and follows the header. The payload length can be calculated as:

::

    Payload Length = Message Length - Header Size

Most messages use the G90CloudMessage class as base which combines the header with the command-specific payload, see
`src/pyg90alarm/cloud/messages.py <../../src/pyg90alarm/cloud/messages.py>`_.