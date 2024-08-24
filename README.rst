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

It mightn't possible to list every system supported by the package due to
manufacturers name the products differently.  Here is the list of hardware
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

Enabling device notifications
=============================

There is a hidden device capability to send protocol notifications over the
WiFi interface. The notifications are done using broadcast UDP packets with
source/destination ports being ``45000:12901`` (non-configurable), and sent when
the device has IP address of its WiFi interface set to ``10.10.10.250``. That is
the same IP the device will allocate to the WiFi interface when AP (access
point is enabled). Please note enabling the AP *is not* required for the
notifications to be sent, only the IP address matters. Likely the firmware does
a check internally and enables those when corresponding IP address is found on
the WiFi interface.

Please see
`protocol documentation <https://pyg90alarm.readthedocs.io/en/stable/protocol.html>`_
for further details on the device notifications.

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

Quick start
===========

.. code:: shell

   pip install pyg90alarm

Documentation
=============

Please see `online documentation <https://pyg90alarm.readthedocs.io>`_ for
details on the protocol, its security, supported commands and the API package
provides.
