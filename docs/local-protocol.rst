G90 alarm panel protocol
========================

.. contents::

There are two protocols a G90 alarm system uses: one towards its own cloud and
another for the clients on local network over WiFi connection.

By the time of writing the following protocol versions are in use:

* Cloud: version 1.1
* Local: version 1.2

.. note:: The rest of the document describes only the local protocol, version 1.2

The local protocol is UDP based, using destination port (alarm panel side) of
``12368``. It has been noticed the vendor provided applications (at least, on iOS)
uses source port ``45000`` when sending protocol commands to the panel,
although further experimentation revealed ephemeral ports could be used
instead.

The protocol commands are text based using JSON encoded payload and ``utf-8``
encoding. See below for requests and responses wire format.

Security
--------

.. warning:: The local protocol *does not* provide any security, neither
   authentication, authorization or encryption.

That translates to:

* Any client on the local network can successfully send the protocol commands
  to the panel, including arming, disarming, configuring etc.
* The protocol expects both requests and responses in clear text

You should consider implementing network controls to, at least, limit on what
clients could interact with the alarm control panel. The implementation might
consider firewall rules, VLANs and other measures available in the network
equipment you user

Request
-------

The protocol request uses the following format, where ``ISTART`` and ``IEND``
are always sent as start/end markers, and the request should be terminated with
binary zero (shown below as ``\0``):

:samp:`ISTART{payload}IEND\\0`

In a generic form the ``payload`` is JSON encoded array contains following elements:

:samp:`[{code},{subcode},[code,[parameters,...]]]``

Typically, both ``code`` and ``subcode`` contain equal values and specify the
command code being sent.

.. note:: Both elements are encoded as integers not strings!

If the command expects parameters, they are provided as nested array, where
``code`` is the first element and duplicates ``code`` from the parent.
Remaining elements in the nested JSON array represent the parameters:

:samp:`ISTART[{code},{subcode}[{code},[parameters,...]]]IEND\\0`

If the command doesn't expect any parameters the request should contain empty
JSON string ``""`` for the nested array:

:samp:`ISTART[{code},{subcode},""]IEND\\0`

Some examples:

- Get host config:

  :samp:`ISTART[106,106,""]IEND\0`

- Turn on device (relay) with ID 12 and subindex 2 (3rd port of multichannel
  device):

  :samp:`ISTART[137,137,[137,[12,0,2]]]IEND\0`


Response
--------

Command responses has structure similar to the requests with regards to
start/end markers, terminator and string encoding. Generic format is:

:samp:`ISTART[{payload}]IEND\\0`

If response doesn't contain ant data it will have only start/end markers and terminator:

:samp:`ISTARTIEND\\0`

In a generic form the ``payload`` is JSON encoded array contains following elements:

:samp:`[{code},[response]]`

The ``code`` duplicates one send in the request and could be used to verify the
response if for the command sent previously.
The ``response`` is the JSON array containing command-specific response.

Some examples:

- Host status response (command ``100``):

  :samp:`ISTART[100,[3,"{panel phone number}","TSV018-C3SIA","205","206"]]IEND`

  Where ``TSV018-C3SIA`` is product name, ``205`` is HW version of MCU (main
  unit) and ``206`` is HW version of Wifi module.

Pagination
----------

Certain commands operate over list of records and require pagination.
Such commands require pagination data to be sent in the request, indicating
range of records requested - :samp:`[{start record},{end record}]`:

:samp:`ISTART[{code},{subcode},[{code},[{start record},{end record}]]]IEND\\0`

Both ``start record`` and ``end record`` are one-based and indicate the
inclusive range of records.

Response to paginated commands comes as JSON array with pagination header as the first element:

:samp:`ISTART[{code},[[{total records},{start record},{count}],[{response element,...}]]]IEND\\0`

Same as for regular commands, the ``code`` duplicates one sent in the request.
The pagination header being first element in the payload array has following
fields:

- ``total records`` total number of records available (one-based)
- ``start record`` the index of the starting record (one-based)
- ``count`` number of records returned

The protocol seems correctly handle the scenario requesting the number of
records larger then those available (difference between ``end record`` and
``start record``), although only if ``start record`` is within available
records - if ``start record`` specifies one outside of the range available the
device will return empty response.


Notification protocol
---------------------

The alarm panel sends notifications and alerts on various events. The
notifications are send unconditionally, that is you cannot disable them, while
alerts are only sent if enabled in the device.

To receive the notifications from the device you need to follow the steps
outlined in :ref:`Enabling device notifications`.

The device uses UDP protocol and ``12901`` target port, each notification is
sent in separate packets having the following structure:

:samp:`[{message ID},[{message code},[data]]]\\0`

All messages are terminated with binary zero (shown below as ``\0``), and text
uses ``utf-8`` encoding.

Data varies across different notification and alert types, see
`pyg90alarm/device_notifications.py <../../src/pyg90alarm/device_notifications.py>`_. 
