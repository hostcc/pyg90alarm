# Copyright (c) 2021 Ilia Sotnikov
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
Definies different constants for G90 alarm panel.
"""
from __future__ import annotations
from enum import IntEnum
from typing import Optional

REMOTE_PORT = 12368
REMOTE_TARGETED_DISCOVERY_PORT = 12900
LOCAL_TARGETED_DISCOVERY_PORT = 12901
LOCAL_NOTIFICATIONS_HOST = '0.0.0.0'
LOCAL_NOTIFICATIONS_PORT = 12901

CMD_PAGE_SIZE = 10


class G90Commands(IntEnum):
    """
    Defines the alarm panel commands and their codes.

    The list consists of the entities known so far, and does not pretend to be
    comprehensive or complete.
    """

    def __new__(cls, value: int, doc: Optional[str] = None) -> G90Commands:
        """
        Allows to set the docstring along with the value to enum entry.
        """
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.__doc__ = doc
        return obj

    NONE = (0, """
        Pseudo command, to be used for proper typing with subclasses of
        `G90BaseCommand` invoking its constructor but implementing special
        processing
    """)

    # Host status
    GETHOSTSTATUS = (100, 'Get host status')
    SETHOSTSTATUS = (101, 'Set host status')
    # Host info
    GETHOSTINFO = 206
    # History
    GETHISTORY = 200
    # Sensors
    GETSENSORLIST = (102, """
        Get list of sensors

        .. note:: Paginated command, see :py:class:`.G90PaginatedResult`
    """)
    SETSINGLESENSOR = 103
    DELSENSOR = 131
    ADDSENSOR = 156
    LEARNSENSOR = 157
    CANCELLEARNSENSOR = 163
    DELALLSENSORS = 202
    # Switches (relays)
    ADDDEVICE = 134
    REGDEVICE = 135
    DELDEVICE = 136
    CONTROLDEVICE = 137
    GETDEVICELIST = (138, """
        Get list of devices (switches)

        .. note:: Paginated command, see :py:class:`.G90PaginatedResult`
    """)
    GETSINGLEDEVICE = 139
    SETSINGLEDEVICE = 140
    DELALLDEVICES = 203
    # Host config
    GETHOSTCONFIG = 106
    SETHOSTCONFIG = 107
    SETALMPHONE = 108
    SETAUTOARM = 109
    # Wireless sirens
    GETSIREN = 110
    SETSIREN = 111
    # Alarm phones, notifications
    GETALMPHONE = 114
    GETAUTOARM = 115
    SETNOTICEFLAG = 116
    GETNOTICEFLAG = 117
    # Factory reset
    SETFACTORY = 118
    GETALARM = 119
    # Rooms
    SETROOMINFO = 141
    GETROOMINFO = 142
    ADDROOM = 158
    DELROOM = 159
    # Scenes
    ADDSCENE = 143
    DELSCENE = 144
    CTLSCENE = 145
    GETSCENELIST = (146, """
        Get list of scenes

        .. note:: Paginated command, see :py:class:`.G90PaginatedResult`
    """)
    GETSINGLESCENE = 147
    SETSINGLESCENE = 148
    GETROOMANDSCENE = 149
    DELALLSCENES = 204
    # IFTTT (scenarios)
    ADDIFTTT = 150
    DELIFTTT = 151
    GETIFTTTLIST = (152, """
        Get list of if-then-else scenarios

        .. note:: Paginated command, see :py:class:`.G90PaginatedResult`
    """)
    GETSINGLEIFTTT = 153
    SETSINGLEIFTTT = 154
    IFTTTREQTIMERID = 164
    DELALLIFTTT = 205
    # Data CRC
    GETUSERDATACRC = 160
    # Fingerprint scanners
    GETFPLOCKLIST = (165, """
        Get list of fingerprint scanners

        .. note:: Paginated command, see :py:class:`.G90PaginatedResult`
    """)
    SETFPLOCKNAME = 166
    GETFPLOCKUSERNAME = 167
    SETFPLOCKUSERNAME = 168
    DELALLLOCK = 223
    # Miscellaneous
    GETAPINFO = 212
    PINGBYGPRS = 218
    PING = 219


class G90MessageTypes(IntEnum):
    """
    Defines message types (codes) from messages coming from the alarm panel.
    """
    NOTIFICATION = 170
    ALERT = 208


class G90NotificationTypes(IntEnum):
    """
    Defines types of notifications sent by the alarm panel.
    """
    ARM_DISARM = 1
    SENSOR_ADDED = 4
    SENSOR_ACTIVITY = 5
    DOOR_OPEN_WHEN_ARMING = 6
    FIRMWARE_UPDATING = 8


class G90ArmDisarmTypes(IntEnum):
    """
    Defines arm/disarm states of the device, applicable both for setting device
    state and one the device sends in notification messages.
    """
    ARM_AWAY = 1
    ARM_HOME = 2
    DISARM = 3
    ALARMED = 4


class G90AlertTypes(IntEnum):
    """
    Defines types of alerts sent by the alarm panel.
    """
    HOST_SOS = 1
    STATE_CHANGE = 2
    ALARM = 3
    SENSOR_ACTIVITY = 4
    # Retained for compatibility, deprecated
    DOOR_OPEN_CLOSE = 4


class G90AlertSources(IntEnum):
    """
    Defines possible sources of the alert sent by the panel.
    """
    DEVICE = 0
    SENSOR = 1
    TAMPER = 3
    REMOTE = 10
    RFID = 11
    DOORBELL = 12
    FINGERPRINT = 15


class G90AlertStates(IntEnum):
    """
    Defines possible states of the alert sent by the panel.
    """
    DOOR_CLOSE = 0
    DOOR_OPEN = 1
    SOS = 2
    TAMPER = 3
    LOW_BATTERY = 4


class G90AlertStateChangeTypes(IntEnum):
    """
    Defines types of alert for device state changes.
    """
    AC_POWER_FAILURE = 1
    AC_POWER_RECOVER = 2
    DISARM = 3
    ARM_AWAY = 4
    ARM_HOME = 5
    LOW_BATTERY = 6
    WIFI_CONNECTED = 7
    WIFI_DISCONNECTED = 8


class G90HistoryStates(IntEnum):
    """
    Defines possible states for history entities.
    """
    DOOR_CLOSE = 1
    DOOR_OPEN = 2
    TAMPER = 3
    ALARM = 4
    AC_POWER_FAILURE = 5
    AC_POWER_RECOVER = 6
    DISARM = 7
    ARM_AWAY = 8
    ARM_HOME = 9
    LOW_BATTERY = 10
    WIFI_CONNECTED = 11
    WIFI_DISCONNECTED = 12
    REMOTE_BUTTON_ARM_AWAY = 13
    REMOTE_BUTTON_ARM_HOME = 14
    REMOTE_BUTTON_DISARM = 15
    REMOTE_BUTTON_SOS = 16


class G90RemoteButtonStates(IntEnum):
    """
    Defines possible states for remote control buttons.
    """
    ARM_AWAY = 0
    ARM_HOME = 1
    DISARM = 2
    SOS = 3
