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
Remaining elements in the nested list represent the parameters.

If the command doesn't expect any parameters the request should contain empty
JSON string ``""`` for the nested array:

:samp:`ISTART[{code},{subcode},""]IEND\\0`

Some examples:

- Get host config:

  ``ISTART[106,106,""]IEND\0``
- Turn on device (relay) with ID 12 and subindex 2 (3rd port of multichannel
  device):

  ``ISTART[137,137,[137,[12,0,2]]]IEND\0``


Response
--------

  ``ISTART[payload]IEND\0``

  ``ISTARTIEND\0``

  ``ISTART[code,[response]]IEND\0``

Pagination
----------

Notification protocol
---------------------
