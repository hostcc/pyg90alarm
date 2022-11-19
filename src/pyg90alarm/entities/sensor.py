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

import logging
from collections import namedtuple
from enum import IntEnum, IntFlag
from ..definitions.sensors import SENSOR_DEFINITIONS
from ..const import G90Commands

# Common protocol fields across read and write operations
COMMON_FIELDS = [
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
]

# Incoming (read operation) protocol fields
INCOMING_FIELDS = COMMON_FIELDS + [
    'mask',
    'private_data',
]

# Outgoing (write operation) protocol fields
OUTGOING_FIELDS = COMMON_FIELDS + [
    'rx',
    'tx',
    'private_data',
]


class G90SensorReservedFlags(IntFlag):
    """
    Reserved flags of the sensor.

    :meta private:
    """
    NONE = 0
    CAN_READ = 16
    CAN_READ_EXT = 32
    CAN_WRITE = 1


class G90SensorUserFlags(IntFlag):
    """
    User flags of the sensor.

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
    Protocol types for the sensors.

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
    Sensor types.

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
    NIGHTLIGHT = 138
    SOCKET_2_4G = 140
    SIREN_2_4G = 141
    SWITCH_2_4G = 142
    TOUCH_SWITCH_2_4G = 143
    CURTAIN_2_4G = 144
    CORD_DEV = 254
    UNKNOWN = 255


_LOGGER = logging.getLogger(__name__)


class G90Sensor:  # pylint:disable=too-many-instance-attributes
    """
    Interacts with sensor on G90 alarm panel.

    :param args: Pass-through positional arguments for for interpreting
     protocol fields
    :param parent: Instance of :class:`.G90Alarm` the sensor is associated
     with
    :type parent: :class:`.G90Alarm`
    :param int subindex: Index of the sensor within multi-channel devices
     (those having multiple nodes)
    :param int proto_idx: Index of the sensor within list of sensors as
     retrieved from the alarm panel
    :param kwargs: Pass-through keyword arguments for for interpreting protocol
     fields
    """
    def __init__(self, *args, parent, subindex, proto_idx, **kwargs):
        self._protocol_incoming_data_kls = (
            namedtuple('G90SensorIncomingData', INCOMING_FIELDS)
        )
        self._protocol_outgoing_data_kls = (
            namedtuple('G90SensorOutgoingData', OUTGOING_FIELDS)
        )
        self._protocol_data = self._protocol_incoming_data_kls(*args, **kwargs)
        self._parent = parent
        self._subindex = subindex
        self._occupancy = False
        self._state_callback = None
        self._proto_idx = proto_idx

        self._definition = None
        # Get sensor definition corresponds to the sensor type/subtype if any
        for s_def in SENSOR_DEFINITIONS:
            if (
                s_def.type == self._protocol_data.type_id
                and s_def.subtype == self._protocol_data.subtype  # noqa:W503
            ):
                self._definition = s_def
                break

    @property
    def name(self):
        """
        Returns sensor name, accounting for multi-channel entities (single
        protocol entity results in multiple :class:`.G90Sensor` instances).

        :return: Sensor name
        :rtype: str
        """
        if self._protocol_data.node_count == 1:
            return self._protocol_data.parent_name
        return f'{self._protocol_data.parent_name}#{self._subindex + 1}'

    @property
    def state_callback(self):
        """
        Returns state callback the sensor might have set.

        :return: Sensor state callback
        :rtype: object
        """
        return self._state_callback

    @state_callback.setter
    def state_callback(self, value):
        """
        Sets callback for the state changes of the sensor.

        :param object value: Sensor state callback
        """
        self._state_callback = value

    @property
    def occupancy(self):
        """
        Occupancy (occupied/not occupied, or triggered/not triggered)
        for the sensor.

        :return: Sensor occupancy
        :rtype: bool
        """
        return self._occupancy

    @occupancy.setter
    def occupancy(self, value):
        """
        Sets occupancy state for the sensor.

        :param bool value: Sensor occupancy
        """
        self._occupancy = value

    @property
    def protocol(self):
        """
        Returns protocol type of the sensor.

        :return: Protocol type
        :rtype: int
        """
        return G90SensorProtocols(self._protocol_data.protocol_id)

    @property
    def type(self):
        """
        Returns type of the sensor.

        :return: Sensor type
        :rtype: int
        """
        return G90SensorTypes(self._protocol_data.type_id)

    @property
    def reserved(self):
        """
        Returns reserved flags (read/write mode) for the sensor.

        :return: Reserved flags
        :rtype: int
        """
        return G90SensorReservedFlags(self._protocol_data.reserved_data)

    @property
    def user_flag(self):
        """
        Returns user flags for the sensor (disabled/enabled, arming type etc).

        :return: User flags
        :rtype: int
        """
        return G90SensorUserFlags(self._protocol_data.user_flag_data)

    @property
    def node_count(self):
        """
        Returns number of nodes (channels) for the sensor.

        :return: Number of nodes
        :rtype: int
        """
        return self._protocol_data.node_count

    @property
    def parent(self):
        """
        Returns parent :class:`.G90Alarm` instance the sensor is associated
        with.

        :return: Parent :class:`.G90Alarm` instance
        :rtype: :class:`.G90Alarm`
        """
        return self._parent

    @property
    def index(self):
        """
        Returns index (internal position) of the sensor in the G90 alarm panel.

        :return: Internal sensor position
        :rtype: int
        """
        return self._protocol_data.index

    @property
    def subindex(self):
        """
        Returns index of the sensor within multi-node device.

        :return: Index of sensor in multi-node device.
        :rtype: int
        """
        return self._subindex

    @property
    def supports_enable_disable(self):
        """
        Indicates if disabling/enabling the sensor is supported.

        :return: Support for enabling/disabling the sensor
        :rtype: bool
        """
        return self._definition is not None

    @property
    def enabled(self):
        """
        Indicates if the sensor is enabled.

        :return: If sensor is enabled
        :rtype: bool
        """
        return self.user_flag & G90SensorUserFlags.ENABLED

    async def set_enabled(self, value):
        """
        Sets disabled/enabled state of the sensor.

        :param bool value: Whether to enable or disable the sensor
        """
        if not self.supports_enable_disable:
            _LOGGER.warning(
                'Manipulating with enable/disable for sensor index=%s'
                ' is unsupported - no sensor definition for'
                ' type=%s, subtype=%s',
                self.index,
                self._protocol_data.type_id,
                self._protocol_data.subtype
            )

            return

        # Refresh actual sensor data from the alarm panel before modifying it.
        # This implies the sensor is at the same position within sensor list
        # (`_proto_index`) as it has been read initially from the alarm panel
        # when instantiated.
        _LOGGER.debug(
            'Refreshing sensor at index=%s, position in protocol list=%s',
            self.index, self._proto_idx
        )
        sensors = self.parent.paginated_result(
            G90Commands.GETSENSORLIST,
            start=self._proto_idx, end=self._proto_idx
        )

        # Compare actual sensor data from what the sensor has been instantiated
        # from, and abort the operation if out-of-band changes are detected.
        _sensor_pos, sensor_data = [x async for x in sensors][0]
        if self._protocol_incoming_data_kls(
            *sensor_data
        ) != self._protocol_data:
            _LOGGER.error(
                "Sensor index=%s '%s' has been changed externally,"
                " refusing to alter its enable/disable state",
                self.index,
                self.name
            )
            return

        # Modify the value of the user flag setting enabled/disabled one
        # appropriately.
        user_flag = self.user_flag
        if value:
            user_flag |= G90SensorUserFlags.ENABLED
        else:
            user_flag &= ~G90SensorUserFlags.ENABLED

        # Re-instantiate the protocol data with modified user flags
        _data = self._protocol_data._asdict()
        _data['user_flag_data'] = user_flag
        self._protocol_data = self._protocol_incoming_data_kls(**_data)

        _LOGGER.debug(
            'Sensor index=%s: %s enabled flag, resulting user_flag %s',
            self._protocol_data.index,
            'Setting' if value else 'Clearing',
            self.user_flag
        )

        # Generate protocol data from write operation, deriving values either
        # from fields read from the sensor, or from the sensor definition - not
        # all fields are present during read, only in definition.
        outgoing_data = self._protocol_outgoing_data_kls(
            parent_name=self._protocol_data.parent_name,
            index=self._protocol_data.index,
            room_id=self._protocol_data.room_id,
            type_id=self._protocol_data.type_id,
            subtype=self._protocol_data.subtype,
            timeout=self._protocol_data.timeout,
            user_flag_data=self._protocol_data.user_flag_data,
            baudrate=self._protocol_data.baudrate,
            protocol_id=self._protocol_data.protocol_id,
            reserved_data=self._definition.reserved_data,
            node_count=self._protocol_data.node_count,
            rx=self._definition.rx,
            tx=self._definition.tx,
            private_data=self._definition.private_data,
        )
        # Modify the sensor
        await self._parent.command(
            G90Commands.SETSINGLESENSOR, list(outgoing_data)
        )

    def __repr__(self):
        """
        Returns string representation of the sensor.

        :return: String representation
        :rtype: str
        """
        return super().__repr__() + f'(name={str(self.name)}' \
            f' type={str(self.type)}' \
            f' protocol={str(self.protocol)}' \
            f' occupancy={self.occupancy}' \
            f' user flag={str(self.user_flag)}' \
            f' reserved={str(self.reserved)})'
