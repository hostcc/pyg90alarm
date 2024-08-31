# Copyright (c) 2022 Ilia Sotnikov
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
Sensor definitions for G90 devices, required when modifying them since writing
a sensor to the device requires values not present on read.
"""
from typing import NamedTuple
from enum import IntEnum


class SensorMatchMode(IntEnum):
    """
    Defines compare (match) mode for the sensor.
    """
    ALL = 0
    ONLY20BITS = 1
    ONLY16BITS = 2


class SensorRwMode(IntEnum):
    """
    Defines read/write mode for the sensor.
    """
    READ = 0
    WRITE = 1
    READ_WRITE = 2


class SensorDefinition(NamedTuple):
    """
    Holds sensor definition data.
    """
    type: int
    subtype: int
    rx: int
    tx: int
    private_data: str
    rwMode: SensorRwMode
    matchMode: SensorMatchMode

    @property
    def reserved_data(self) -> int:
        """
        Sensor's 'reserved_data' field to be written, combined of match
        and RW mode values bitwise.
        """
        return self.matchMode.value << 4 | self.rwMode.value


SENSOR_DEFINITIONS = [
    # Cord Door Sensor
    SensorDefinition(
        type=126,
        subtype=1,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # Cord Glass Sensor
    SensorDefinition(
        type=126,
        subtype=2,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # Cord Gas Sensor
    SensorDefinition(
        type=126,
        subtype=3,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # Cord Smoke Sensor
    SensorDefinition(
        type=126,
        subtype=4,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # Cord SOS Sensor
    SensorDefinition(
        type=126,
        subtype=5,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # Cord Vibration Sensor
    SensorDefinition(
        type=126,
        subtype=6,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # Cord Water Sensor
    SensorDefinition(
        type=126,
        subtype=7,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # Cord Beam Sensor
    SensorDefinition(
        type=126,
        subtype=9,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # Cord PIR motion sensor
    SensorDefinition(
        type=126,
        subtype=8,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # Cord RFID Sensor
    SensorDefinition(
        type=126,
        subtype=11,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # Cord Bell Sensor
    SensorDefinition(
        type=126,
        subtype=12,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # Cord Device
    SensorDefinition(
        type=254,
        subtype=0,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.WRITE,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # Socket S07
    SensorDefinition(
        type=128,
        subtype=3,
        rx=0,
        tx=2,
        private_data='060A0600',
        rwMode=SensorRwMode.WRITE,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # Socket JDQ
    SensorDefinition(
        type=128,
        subtype=0,
        rx=0,
        tx=2,
        private_data='0707070B0B0D0D0E0E00',
        rwMode=SensorRwMode.WRITE,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # Socket Relay (single channel)
    SensorDefinition(
        type=128,
        subtype=1,
        rx=0,
        tx=2,
        private_data='07070700',
        rwMode=SensorRwMode.WRITE,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # Socket Switch
    SensorDefinition(
        type=128,
        subtype=4,
        rx=0,
        tx=2,
        private_data='050D0500',
        rwMode=SensorRwMode.WRITE,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # Socket Switch (3 channel)
    SensorDefinition(
        type=128,
        subtype=5,
        rx=0,
        tx=2,
        private_data='070A0E080D060B00',
        rwMode=SensorRwMode.WRITE,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # Socket Switch (4 channel)
    SensorDefinition(
        type=128,
        subtype=6,
        rx=0,
        tx=2,
        private_data='0B0D0E0B0C090A070800',
        rwMode=SensorRwMode.WRITE,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # Rolling curtain
    SensorDefinition(
        type=130,
        subtype=0,
        rx=0,
        tx=7,
        private_data='070B0E0D0C09030100',
        rwMode=SensorRwMode.WRITE,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # Curtain
    SensorDefinition(
        type=130,
        subtype=1,
        rx=0,
        tx=7,
        private_data='0804010200',
        rwMode=SensorRwMode.WRITE,
        matchMode=SensorMatchMode.ONLY16BITS
    ),
    # Sliding window
    SensorDefinition(
        type=130,
        subtype=1,
        rx=0,
        tx=7,
        private_data='0E0B0E0D0C09030100',
        rwMode=SensorRwMode.WRITE,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # Push Window curtain
    SensorDefinition(
        type=130,
        subtype=2,
        rx=0,
        tx=7,
        private_data='070B0E0D0C09030100',
        rwMode=SensorRwMode.WRITE,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # Air Conditioner
    SensorDefinition(
        type=133,
        subtype=0,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.WRITE,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # TV
    SensorDefinition(
        type=135,
        subtype=0,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.WRITE,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # Infrared Transcoder
    SensorDefinition(
        type=145,
        subtype=0,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.WRITE,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # Siren SS08
    SensorDefinition(
        type=129,
        subtype=0,
        rx=0,
        tx=2,
        private_data='FEFEF600',
        rwMode=SensorRwMode.WRITE,
        matchMode=SensorMatchMode.ONLY16BITS
    ),
    # Siren SS07A
    SensorDefinition(
        type=129,
        subtype=4,
        rx=0,
        tx=2,
        private_data='FEFEF600',
        rwMode=SensorRwMode.WRITE,
        matchMode=SensorMatchMode.ONLY16BITS
    ),
    # Siren SS04
    SensorDefinition(
        type=129,
        subtype=5,
        rx=0,
        tx=2,
        private_data='FCFCCF00',
        rwMode=SensorRwMode.WRITE,
        matchMode=SensorMatchMode.ONLY16BITS
    ),
    # Siren SS02B
    SensorDefinition(
        type=129,
        subtype=1,
        rx=0,
        tx=2,
        private_data='FCFCCF00',
        rwMode=SensorRwMode.WRITE,
        matchMode=SensorMatchMode.ONLY16BITS
    ),
    # Solar-powered siren
    SensorDefinition(
        type=129,
        subtype=2,
        rx=0,
        tx=2,
        private_data='FEFEFD00',
        rwMode=SensorRwMode.WRITE,
        matchMode=SensorMatchMode.ONLY16BITS
    ),
    # Night Light
    SensorDefinition(
        type=138,
        subtype=0,
        rx=0,
        tx=2,
        private_data='060A0600',
        rwMode=SensorRwMode.WRITE,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # Socket_2.4G
    SensorDefinition(
        type=140,
        subtype=1,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.WRITE,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # Siren_2.4G
    SensorDefinition(
        type=141,
        subtype=1,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.WRITE,
        matchMode=SensorMatchMode.ONLY16BITS
    ),
    # Switch 2.4G Type 2
    SensorDefinition(
        type=142,
        subtype=2,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.WRITE,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # Switch 2.4G Type 1
    SensorDefinition(
        type=143,
        subtype=1,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.WRITE,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # Switch 2.4G Type 2
    SensorDefinition(
        type=143,
        subtype=2,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.WRITE,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # Switch 2.4G Type 3
    SensorDefinition(
        type=143,
        subtype=3,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.WRITE,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # Switch 2.4G Type 4
    SensorDefinition(
        type=143,
        subtype=4,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.WRITE,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # Curtain 2.4G
    SensorDefinition(
        type=144,
        subtype=1,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.WRITE,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # Door Sensor WDS07
    SensorDefinition(
        type=1,
        subtype=0,
        rx=5,
        tx=0,
        private_data='F100f5017d02f803f90400',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ONLY16BITS
    ),
    # Door Sensor
    SensorDefinition(
        type=1,
        subtype=1,
        rx=2,
        tx=0,
        private_data='0001020400',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # Door Sensor WRDS01
    SensorDefinition(
        type=1,
        subtype=3,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ALL
    ),
    # Door Sensor
    SensorDefinition(
        type=1,
        subtype=2,
        rx=5,
        tx=0,
        private_data='F100f5017d02f803f904',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ONLY16BITS
    ),
    # Glass Break Sensor BLPS
    SensorDefinition(
        type=2,
        subtype=0,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ALL
    ),
    # Gas Detector WGD01
    SensorDefinition(
        type=3,
        subtype=0,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ALL
    ),
    # Smoke Detector WSD02
    SensorDefinition(
        type=4,
        subtype=0,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ALL
    ),
    # Smoke Detector WSD04
    SensorDefinition(
        type=4,
        subtype=1,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ALL
    ),
    # Panic Button WEB01
    SensorDefinition(
        type=5,
        subtype=1,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ALL
    ),
    # Panic Button WEB03
    SensorDefinition(
        type=5,
        subtype=0,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ALL
    ),
    # Shock Sensor WSS01
    SensorDefinition(
        type=6,
        subtype=0,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ALL
    ),
    # Water Detector LSTC02
    SensorDefinition(
        type=7,
        subtype=1,
        rx=0,
        tx=0,
        private_data='',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ALL
    ),
    # Water Detector LSTC01
    SensorDefinition(
        type=7,
        subtype=0,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ALL
    ),
    # PIR motion sensor WMS08
    SensorDefinition(
        type=8,
        subtype=3,
        rx=3,
        tx=0,
        private_data='06000301020200',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # PIR motion sensor WMS08B
    SensorDefinition(
        type=8,
        subtype=12,
        rx=3,
        tx=0,
        private_data='060003010202000314',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # PIR motion sensor ODPIR
    SensorDefinition(
        type=8,
        subtype=0,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ALL
    ),
    # PIR motion sensor N650
    SensorDefinition(
        type=8,
        subtype=5,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ALL
    ),
    # PIR motion sensor WPD02
    SensorDefinition(
        type=8,
        subtype=6,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ALL
    ),
    # PIR motion sensor WCMS02
    SensorDefinition(
        type=8,
        subtype=8,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ALL
    ),
    # PIR motion sensor CWMS01
    SensorDefinition(
        type=8,
        subtype=9,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ALL
    ),
    # PIR motion sensor WMS04
    SensorDefinition(
        type=8,
        subtype=11,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ALL
    ),
    # PIR motion sensor WMS07
    SensorDefinition(
        type=8,
        subtype=2,
        rx=3,
        tx=0,
        private_data='04000801020200',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # PIR motion sensor ODPIR03
    SensorDefinition(
        type=8,
        subtype=4,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ALL
    ),
    # PIR motion sensor WPD01
    SensorDefinition(
        type=8,
        subtype=7,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ALL
    ),
    # PIR motion sensor PIR Ceiling
    SensorDefinition(
        type=8,
        subtype=1,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ALL
    ),
    # Beams ABT
    SensorDefinition(
        type=9,
        subtype=0,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ALL
    ),
    # Beams ABE
    SensorDefinition(
        type=9,
        subtype=1,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ALL
    ),
    # Beams ABH
    SensorDefinition(
        type=9,
        subtype=2,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ALL
    ),
    # Remote RMC08
    SensorDefinition(
        type=10,
        subtype=1,
        rx=4,
        tx=0,
        private_data='0d000b010e02070300',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # Remote RMC07
    SensorDefinition(
        type=10,
        subtype=0,
        rx=4,
        tx=0,
        private_data='cf00fc01f3023f0300',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ONLY16BITS
    ),
    # Remote RMC02
    SensorDefinition(
        type=10,
        subtype=4,
        rx=4,
        tx=0,
        private_data='cf00fc01f3023f0300',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ONLY16BITS
    ),
    # Remote
    SensorDefinition(
        type=10,
        subtype=2,
        rx=3,
        tx=0,
        private_data='07000602050300',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # RFID K07
    SensorDefinition(
        type=11,
        subtype=1,
        rx=11,
        tx=0,
        private_data='0e0007010d020b03010402050c060a0709080809060a00',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # Door Bell WDB
    SensorDefinition(
        type=12,
        subtype=1,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ALL
    ),
    # TouchID Detector
    SensorDefinition(
        type=13,
        subtype=1,
        rx=4,
        tx=0,
        private_data='07000e010d020b0300',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # SOS Watch
    SensorDefinition(
        type=14,
        subtype=0,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ONLY16BITS
    ),
    # Fingerprint Lock
    SensorDefinition(
        type=15,
        subtype=1,
        rx=0,
        tx=2,
        private_data='00',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ONLY16BITS
    ),
    # Sub Host SS08S
    SensorDefinition(
        type=16,
        subtype=0,
        rx=0,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ALL
    ),
    # Gas Valve Detector WGD02
    SensorDefinition(
        type=18,
        subtype=0,
        rx=2,
        tx=1,
        private_data='09000801ff0e0e',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
    # Remote 2.4G RMC2.4G
    SensorDefinition(
        type=17,
        subtype=4,
        rx=4,
        tx=0,
        private_data='00',
        rwMode=SensorRwMode.READ,
        matchMode=SensorMatchMode.ONLY20BITS
    ),
]
