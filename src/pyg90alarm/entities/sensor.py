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
Provides interface to sensors of G90 alarm panel.
"""

from collections import namedtuple
from enum import IntEnum, IntFlag

INCOMING_FIELDS = [
    'parent_name',
    'index',
    'room_id',
    'type_id',
    'subtype',
    'timeout',
    'user_flag_data',
    'baudrate',
    'protocol_id',
    'reserved_data',
    'node_count',
    'mask',
    'private',
    'parent',
    'subindex'
]


class G90SensorReservedFlags(IntFlag):
    """
    tbd

    :meta private:
    """
    NONE = 0
    CAN_READ = 16
    CAN_READ_EXT = 32
    CAN_WRITE = 1


class G90SensorUserFlags(IntFlag):
    """
    tbd

    :meta private:
    """
    NONE = 0
    ENABLED = 1
    ARM_DELAY = 2
    DETECT_DOOR = 4
    DOOR_CHIME = 8
    INDEPENDENT_ZONE = 16
    ALERT_WHEN_AWAY_AND_HOME = 32
    ALERT_WHEN_AWAY = 64
    SUPPORTS_UPDATING_SUBTYPE = 512     # Only relevant for cord sensors


class G90SensorProtocols(IntEnum):
    """
    tbd

    :meta private:
    """
    RF_1527 = 0
    RF_2262 = 1
    RF_PRIVATE = 2
    RF_SLIDER = 3
    CORD = 5
    WIFI = 4
    USB = 6


class G90SensorTypes(IntEnum):
    """
    tbd

    :meta private:
    """
    DOOR = 1
    GLASS = 2
    GAS = 3
    SMOKE = 4
    SOS = 5
    VIB = 6
    WATER = 7
    INFRARED = 8
    IN_BEAM = 9
    REMOTE = 10
    RFID = 11
    DOORBELL = 12
    BUTTONID = 13
    WATCH = 14
    FINGER_LOCK = 15
    SUBHOST = 16
    REMOTE_2_4G = 17
    CORD_SENSOR = 126
    SOCKET = 128
    SIREN = 129
    CURTAIN = 130
    SLIDINGWIN = 131
    AIRCON = 136
    TV = 137
    SOCKET_2_4G = 140
    SIREN_2_4G = 141
    SWITCH_2_4G = 142
    TOUCH_SWITCH_2_4G = 143
    CURTAIN_2_4G = 144
    CORD_DEV = 254
    UNKNOWN = 255


class G90Sensor(namedtuple('G90Sensor', INCOMING_FIELDS)):
    """
    tbd
    """
    _occupancy = False
    _state_callback = None

    @property
    def name(self):
        """
        tbd
        """
        if self.node_count == 1:
            return self.parent_name
        return f'{self.parent_name}#{self.subindex + 1}'

    @property
    def enabled(self):
        """
        tbd
        """
        return self.user_flag & G90SensorUserFlags.ENABLED

    @property
    def state_callback(self):
        """
        tbd
        """
        return self._state_callback

    @state_callback.setter
    def state_callback(self, value):
        """
        tbd
        """
        self._state_callback = value

    @property
    def occupancy(self):
        """
        tbd
        """
        return self._occupancy

    @occupancy.setter
    def occupancy(self, value):
        """
        tbd
        """
        self._occupancy = value

    @property
    def protocol(self):
        """
        tbd
        """
        return G90SensorProtocols(self.protocol_id)

    @property
    def type(self):
        """
        tbd
        """
        return G90SensorTypes(self.type_id)

    @property
    def reserved(self):
        """
        tbd
        """
        return G90SensorReservedFlags(self.reserved_data)

    @property
    def user_flag(self):
        """
        tbd
        """
        return G90SensorUserFlags(self.user_flag_data)

    def __repr__(self):
        """
        tbd
        """
        return super().__repr__() + f'(name={str(self.name)}' \
            f' type={str(self.type)}' \
            f' protocol={str(self.protocol)}' \
            f' occupancy={self.occupancy}' \
            f' user flag={str(self.user_flag)}' \
            f' reserved={str(self.reserved)})'
