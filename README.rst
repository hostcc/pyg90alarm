.. image::  https://github.com/hostcc/pyg90alarm/actions/workflows/main.yml/badge.svg?branch=master
   :target: https://github.com/hostcc/pyg90alarm/tree/master
   :alt: Github workflow status
.. image:: https://readthedocs.org/projects/pyg90alarm/badge/?version=stable
   :target: https://pyg90alarm.readthedocs.io/en/stable
   :alt: ReadTheDocs status
.. image:: https://img.shields.io/github/v/release/hostcc/pyg90alarm
   :target: https://github.com/hostcc/pyg90alarm/releases/latest
   :alt: Latest GitHub release
.. image:: https://img.shields.io/pypi/v/pyg90alarm
   :target: https://pypi.org/project/pyg90alarm/
   :alt: Latest PyPI version

Description
===========

Python package to control G90-based alarm systems.

Many manufacturers sell such systems under different brands - Golden Security,
PST, Kerui and others. Those are cheap low-end systems, typically equipped with
WiFi and possible GSM interfaces for connectivity, and support different range
of peripherals:

* Wired and wireless sensors
* Relays (switches)

... and probably others

The package implements asynchronous I/O over most of code paths using
`asyncio <https://docs.python.org/3/library/asyncio.html>`_.

Disclaimer
==========

The author has no affiliation or any relationship to any of the hardware
vendors in question. The code has been created upon many trial and error
iterations.

Motivation
==========

The primary motivation creating the code is the comfort of using the security
system - the mobile applications provided by the vendor, called "Carener", is
slow and crashes sometimes. Instead, it would be awesome to have the system
integrated into larger ecosystems, like Home Assistant, HomeKit and such.
Hence, the code has been created to interact with the security system using
Python, and it opens up a way for further integrations.

Supported hardware
==================

It might not be possible to list every system supported by the package due to
manufacturers naming the products differently.  Here is the list of hardware
known to work with the package:

* `PST G90B Plus <http://www.cameralarms.com/products/auto_dial_alarm_system/185.html>`_

And the list of sensors, actual set of device should be notable larger as many
of other manufacturers produce similar items. The names in parenthesis are
taken from the alarm system documentation, for example, `Home Alarm GB90-Plus <https://archive.org/details/HomeAlarmGB90-Plus/G90B%20plus%20WIFIGSMGPRS%20alarm%20system%20user%20manual/page/n7/mode/2up>`_.

* Wired PIR sensors
* Wireless PIR sensors (WPD01, WMS08)
* Door/window sensors (WDS07, WRDS01)
* Water leak sensors (LSTC01)
* Smoke sensors (WSD02)
* Gas sensors (WGD01)
* Switches/relays (JDQ)

Basically, the alarm system uses 433 MHz communications for the wireless
devices using EV1527, PT2262 protocols. The mobile application also mentions
some devices using 2.4GHz, although details of the protocols haven't been
identified as no such hardware has been available for experimentation.

Known caveats
=============

* Wireless shutter sensor (WRDS01) doesn't send anything on sensor closed, only
  when opened. In contrast, WDS07 wireless door sensor does both.
* Wireless relays (at least JDQ) use same RF code for switching on and off,
  when configured in toggle mode. That means a RF signal repeater will make
  controlling such relays unpredictable, since the code will be sent more than
  once.
* Low battery notifications for wireless sensors (at least for WDS07 and WSD02)
  are often missing, either due to the sensors not sending them or the device
  doesn't receive those.
* Wired sensors toggle on line state change, i.e. those aren't limited to have
  normal closed (NC) or normal open (NO) contacts only. Best used with NC
  contact sensors though, since an intruder cutting the line will trigger the
  alarm.

Device notifications
====================

Local notifications
-------------------

There is a hidden device capability to send protocol notifications over the
WiFi interface, thus called local. The notifications are done using broadcast UDP packets with source/destination ports being ``45000:12901`` (non-configurable), and sent when the device has IP address of its WiFi interface set to ``10.10.10.250``. That is the same IP the device will allocate to the WiFi interface when AP (access point is enabled). Please note enabling the AP *is not* required for the notifications to be sent, only the IP address matters. Likely the firmware does a check internally and enables those when corresponding IP address is found on the WiFi interface.

Depending on your network setup, ensuring the `10.10.10.250` IP address is
allocated to the WiFi interface of the device might be as simple as DHCP
reservation. Please check the documentation of your networking gear on how to
set the IP address allocation up.

.. note:: Since the IP address trick above isn't something the device exposes
   to the user, the functionality might change or even cease functioning upon a
   firmware upgrade!

.. note:: The device notifications in question are fully local with no
   dependency on the cloud or Internet connection on the device.

.. note:: If IP address trick doesn't work for you by a reason, the package
   will still be able to perform the key functions - for example, arming or
   disarming the panel, or reading the list of sensors. However, the sensor
   status will not be reflected and those will always be reported as inactive,
   since there is no way to read their state in a polled manner.

   To work that limitation around the package now supports simulating device
   notifications from periodically polling the history it records - the
   simulation works only for the alerts, not notifications (e.g. notifications
   include low battery events and alike). This also requires the particular
   alert to be enabled in the mobile application, otherwise it won't be
   recorded in the history.

For the local notifications to be enabled the ``G90Alarm.use_local_notifications()`` needs to be called upon constructing an instance of ``G90Alarm`` class, then ``G90Alarm.listen_notifications()`` to start processing those coming from the panel - the code fragment below demonstrates that though being incomplete since callbacks (e.g. ``G90Alarm.on_armdisarm()``) should be set for the actual processing of the notifications.

.. code:: python

   from pyg90alarm import G90Alarm

   # Create an instance of the alarm panel
   alarm = G90Alarm(host='10.10.10.250')
   # Enable local notifications
   await alarm.use_local_notifications()
   # Start listening for notifications
   await alarm.listen_notifications()

Cloud notifications
-------------------

The cloud protocol is native to the panel and is used to interact with mobile application. The package can mimic the cloud server and interpret the messages the panel sends to the cloud, allowing to receive the notifications and alerts.
While the protocol also allows to send commands to the panel, it is not implemented and local protocol is used for that - i.e. when cloud notifications are in use the local protocol still utilized for sending commands to the panel.

The cloud protocol is TCP based and typically interacts with cloud service at known IP address and port (not customizable at panel side). To process the cloud notifications all the traffic from panel towards the cloud (IP address ``47.88.7.61`` and TCP port ``5678`` as of writing) needs to be diverted to the node where the package is running - depending on your network equipment it could be port forwarding, DNAT or other means. It is unclear whether the panel utilizes DNS to resolve the cloud service IP address, hence the documentation only mentions IP-based traffic redirection.

Please see
`the section <docs/cloud-protocol.rst>`_ for further details on the protocol.

The benefit of the cloud notifications is that the panel no longer required to have ``10.10.10.250`` IP address.

The package could act as:

- Standalone cloud server with no Internet connectivity or cloud service
  required at all - good if you'd like to avoid having a vendor service involved. Please note the mobile application will show panel as offline in this mode
- Chained cloud server, where in addition to interpreting the notifications it
  will also forward all packets received from the panel to the cloud server, and pass its responses back to the panel. This allows to have notifications processed by the package and the mobile application working as well.

  .. note:: Sending packets upstream to the known IP address and port of the cloud server might result in those looped back (since traffic from panel to cloud service has to be redirected to the host where package runs), if your network equipment can't account for source address in redirection rules (i.e. limiting the port redirection to the panel's IP address). In that case you'll need another redirection, from the host where the package runs to the cloud service using an IP from your network. That way those two redirection rules will coexist correctly. To illustrate:

   Port forwarding rule 1:

   - Source: panel IP address
   - Destination: 47.88.7.61
   - Port: 5678
   - Redirect to host: host where package runs
   - Redirect to port: 5678 (or other port if you want to use it)


   Port forwarding rule 2 (optional):

   - Source: host where package runs
   - Destination: an IP address from your network
   - Port: 5678 (or other port if you want to use it)
   - Redirect to : 47.88.7.61
   - Redirect to port: 5678

The code fragments below demonstrate how to utilize both modes - please note those are incomplete, since no callbacks are set to process the notifications.

**Standalone mode**

.. code:: python

   from pyg90alarm import G90Alarm

   # Create an instance of the alarm panel
   alarm = G90Alarm(host='<panel IP address>')
   # Enable cloud notifications
   await alarm.use_cloud_notifications(
      # Optional, see note above redirecting cloud traffic from panel
      local_port=5678,
      upstream_host=None
   )
   # Start listening for notifications
   await alarm.listen_notifications()


**Chained mode**

.. code:: python

   from pyg90alarm import G90Alarm

   # Create an instance of the alarm panel
   alarm = G90Alarm(host='<panel IP address>')
   # Enable cloud notifications
   await alarm.use_cloud_notifications(
      # Optional, see note above redirecting cloud traffic from panel
      local_port=5678,
      # See note above re: cloud service and sending packets to it
      upstream_host='47.88.7.61',
      upstream_port=5678
   )
   # Start listening for notifications
   await alarm.listen_notifications()


Quick start
===========

.. code:: shell

   pip install pyg90alarm

Documentation
=============

Please see `online documentation <https://pyg90alarm.readthedocs.io>`_ for
details on the protocol, its security, supported commands and the API package
provides.
