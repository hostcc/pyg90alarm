[![master](https://github.com/hostcc/pyg90alarm/actions/workflows/main.yml/badge.svg?branch=master)](https://github.com/hostcc/pyg90alarm/tree/master)
[![Documentation Status](https://readthedocs.org/projects/pyg90alarm/badge/?version=stable)](https://pyg90alarm.readthedocs.io/en/stable/?badge=stable)

# Description

Python package to control G90-based alarm systems.

Many manufacturers sell such systems under different brands - Golden Security,
PST, Kerui and others. Those are cheap low-end systems, typically equipped with
WiFi and possible GSM interfaces for connectivity, and support different range
of peripherals:
* Wired and wireless sensors
* Relays (switches)

... and probably others

# Disclaimer

The author has no affiliation or any relationship to any of the hardware
vendors in question. The code has been created upon many trial and error
iterations.

# Motivation

The primary motivation creating the code is the comfort of using the security
system - the mobile applications provided by the vendor, called "Carener", is
slow and crashes sometimes. Instead, it would be awesome to have the system
integrated into larger ecosystems, like Home Assistant, HomeKit and such.
Hence, the code has been created to interact with the security system using
Python, and it opens up a way for further integrations.

# Supported hardware

It mightn't possible to list every system supported by the package due to
manufacturers name the products differently.  Here is the list of hardware
known to work with the package:
* [PST G90B Plus](http://www.cameralarms.com/products/auto_dial_alarm_system/185.html)

And the list of sensors, actual set of device should be notable larger as many
of other manufacturers produce similar items. The names in parenthesis are
taken from the alarm system documentation, for example, [Home Alarm GB90-Plus](https://archive.org/details/HomeAlarmGB90-Plus/G90B%20plus%20WIFIGSMGPRS%20alarm%20system%20user%20manual/page/n7/mode/2up).

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

# Quick start

TBD

# Documentation

Please see [online documentation](https://pyg90alarm.readthedocs.io) for details on the protocol, its
security, supported commands and the API package provides.
