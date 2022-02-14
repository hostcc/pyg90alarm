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
tbd
"""

from enum import IntEnum

REMOTE_PORT = 12368
REMOTE_TARGETED_DISCOVERY_PORT = 12900
LOCAL_TARGETED_DISCOVERY_PORT = 12901

CMD_PAGE_SIZE = 10


class G90Commands(IntEnum):
    """
    Defines the alarm panel commands and their codes.

    The list consists of the entities known so far, and does not pretend to be
    comprehensive or complete.
    """
    # Host status
    GETHOSTSTATUS = 100
    SETHOSTSTATUS = 101
    # Host info
    GETHOSTINFO = 206
    # History
    GETHISTORY = 200
    # Sensors
    GETSENSORLIST = 102
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
    GETDEVICELIST = 138
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
    GETSCENELIST = 146
    GETSINGLESCENE = 147
    SETSINGLESCENE = 148
    GETROOMANDSCENE = 149
    DELALLSCENES = 204
    # IFTTT (scenarios)
    ADDIFTTT = 150
    DELIFTTT = 151
    GETIFTTTLIST = 152
    GETSINGLEIFTTT = 153
    SETSINGLEIFTTT = 154
    IFTTTREQTIMERID = 164
    DELALLIFTTT = 205
    # Data CRC
    GETUSERDATACRC = 160
    # Fingerprint scanners
    GETFPLOCKLIST = 165
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
    SENSOR_ACTIVITY = 5


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
    STATE_CHANGE = 2
    ALARM = 3
    DOOR_OPEN_CLOSE = 4


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
