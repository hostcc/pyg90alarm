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
from __future__ import annotations
import logging
from dataclasses import dataclass, asdict, astuple
from typing import (
    Any, Optional, TYPE_CHECKING, Dict
)

from enum import IntEnum, IntFlag
from ..definitions.sensors import SENSOR_DEFINITIONS, SensorDefinition
from ..const import G90Commands
if TYPE_CHECKING:
    from ..alarm import G90Alarm, SensorStateCallback, SensorLowBatteryCallback


@dataclass
class G90SensorCommonData:  # pylint:disable=too-many-instance-attributes
    """
    Common protocol fields across read and write operations
    """
    parent_name: str
    index: int
    room_id: int
    type_id: int
    subtype: int
    timeout: int
    user_flag_data: int
    baudrate: int
    protocol_id: int
    reserved_data: int
    node_count: int


@dataclass
class G90SensorIncomingData(G90SensorCommonData):
    """
    Incoming (read operation) protocol fields
    """
    mask: int
    private_data: str


@dataclass
class G90SensorOutgoingData(G90SensorCommonData):
    """
    Outgoing (write operation) protocol fields
    """
    rx: int  # pylint:disable=invalid-name
    tx: int  # pylint:disable=invalid-name
    private_data: str


class G90SensorReservedFlags(IntFlag):
    """
    Reserved flags of the sensor.
    """
    NONE = 0
    CAN_READ = 16
    CAN_READ_EXT = 32
    CAN_WRITE = 1


class G90SensorUserFlags(IntFlag):
    """
    User flags of the sensor.
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
    def __init__(
        self, *args: Any, parent: G90Alarm, subindex: int, proto_idx: int,
        **kwargs: Any
    ) -> None:
        self._protocol_incoming_data_kls = G90SensorIncomingData
        self._protocol_outgoing_data_kls = G90SensorOutgoingData
        self._protocol_data = self._protocol_incoming_data_kls(*args, **kwargs)
        self._parent = parent
        self._subindex = subindex
        self._occupancy = False
        self._state_callback: Optional[SensorStateCallback] = None
        self._low_battery_callback: Optional[SensorLowBatteryCallback] = None
        self._proto_idx = proto_idx
        self._extra_data: Any = None

        self._definition: Optional[SensorDefinition] = None
        # Get sensor definition corresponds to the sensor type/subtype if any
        for s_def in SENSOR_DEFINITIONS:
            if (
                s_def.type == self._protocol_data.type_id
                and s_def.subtype == self._protocol_data.subtype  # noqa:W503
            ):
                self._definition = s_def
                break

    @property
    def name(self) -> str:
        """
        Returns sensor name, accounting for multi-channel entities (single
        protocol entity results in multiple :class:`.G90Sensor` instances).

        :return: Sensor name
        """
        if self._protocol_data.node_count == 1:
            return self._protocol_data.parent_name
        return f'{self._protocol_data.parent_name}#{self._subindex + 1}'

    @property
    def state_callback(self) -> Optional[SensorStateCallback]:
        """
        Returns state callback the sensor might have set.

        :return: Sensor state callback
        """
        return self._state_callback

    @state_callback.setter
    def state_callback(self, value: SensorStateCallback) -> None:
        """
        Sets callback for the state changes of the sensor.

        :param object value: Sensor state callback
        """
        self._state_callback = value

    @property
    def low_battery_callback(self) -> Optional[SensorLowBatteryCallback]:
        """
        Returns callback the sensor might have set for low battery condition.

        :return: Sensor's low battery callback
        """
        return self._low_battery_callback

    @low_battery_callback.setter
    def low_battery_callback(self, value: SensorLowBatteryCallback) -> None:
        """
        Sets callback for the low battery condition reported by the sensor.

        :param object value: Sensor's low battery callback
        """
        self._low_battery_callback = value

    @property
    def occupancy(self) -> bool:
        """
        Occupancy (occupied/not occupied, or triggered/not triggered)
        for the sensor.

        :return: Sensor occupancy
        """
        return self._occupancy

    @occupancy.setter
    def occupancy(self, value: bool) -> None:
        """
        Sets occupancy state for the sensor.

        :param value: Sensor occupancy
        """
        self._occupancy = value

    @property
    def protocol(self) -> G90SensorProtocols:
        """
        Returns protocol type of the sensor.

        :return: Protocol type
        """
        return G90SensorProtocols(self._protocol_data.protocol_id)

    @property
    def type(self) -> G90SensorTypes:
        """
        Returns type of the sensor.

        :return: Sensor type
        """
        return G90SensorTypes(self._protocol_data.type_id)

    @property
    def subtype(self) -> int:
        """
        Returns type of the sensor.

        :return: Sensor type
        """
        return self._protocol_data.subtype

    @property
    def reserved(self) -> G90SensorReservedFlags:
        """
        Returns reserved flags (read/write mode) for the sensor.

        :return: Reserved flags
        """
        return G90SensorReservedFlags(self._protocol_data.reserved_data)

    @property
    def user_flag(self) -> G90SensorUserFlags:
        """
        Returns user flags for the sensor (disabled/enabled, arming type etc).

        :return: User flags
        """
        return G90SensorUserFlags(self._protocol_data.user_flag_data)

    @property
    def node_count(self) -> int:
        """
        Returns number of nodes (channels) for the sensor.

        :return: Number of nodes
        """
        return self._protocol_data.node_count

    @property
    def parent(self) -> G90Alarm:
        """
        Returns parent instance of alarm panel the sensor is associated
        with.

        :return: Parent instance
        """
        return self._parent

    @property
    def index(self) -> int:
        """
        Returns index (internal position) of the sensor in the G90 alarm panel.

        :return: Internal sensor position
        """
        return self._protocol_data.index

    @property
    def subindex(self) -> int:
        """
        Returns index of the sensor within multi-node device.

        :return: Index of sensor in multi-node device.
        """
        return self._subindex

    @property
    def supports_enable_disable(self) -> bool:
        """
        Indicates if disabling/enabling the sensor is supported.

        :return: Support for enabling/disabling the sensor
        """
        return self._definition is not None

    @property
    def enabled(self) -> bool:
        """
        Indicates if the sensor is enabled.

        :return: If sensor is enabled
        """
        return self.user_flag & G90SensorUserFlags.ENABLED != 0

    async def set_enabled(self, value: bool) -> None:
        """
        Sets disabled/enabled state of the sensor.

        :param value: Whether to enable or disable the sensor
        """
        # Checking private attribute directly, since `mypy` doesn't recognize
        # the check for sensor definition to be defined if done over
        # `self.supports_enable_disable` property
        if not self._definition:
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
        sensors_result = self.parent.paginated_result(
            G90Commands.GETSENSORLIST,
            start=self._proto_idx, end=self._proto_idx
        )
        sensors = [x.data async for x in sensors_result]

        # Abort if sensor is not found
        if not sensors:
            _LOGGER.error(
                'Sensor index=%s not found when attempting to set its'
                ' enable/disable state',
                self.index,
            )
            return

        # Compare actual sensor data from what the sensor has been instantiated
        # from, and abort the operation if out-of-band changes are detected.
        sensor_data = sensors[0]
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
        _data = asdict(self._protocol_data)
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
            G90Commands.SETSINGLESENSOR, list(astuple(outgoing_data))
        )

    @property
    def extra_data(self) -> Any:
        """
        Sets extra data for the sensor, that can be used to store
        caller-specific information and will be carried by the sensor instance.
        """
        return self._extra_data

    @extra_data.setter
    def extra_data(self, val: Any) -> None:
        self._extra_data = val

    def _asdict(self) -> Dict[str, Any]:
        """
        Returns dictionary representation of the sensor.

        :return: Dictionary representation
        """
        return {
            'name': self.name,
            'type': self.type,
            'subtype': self.subtype,
            'index': self.index,
            'subindex': self.subindex,
            'node_count': self.node_count,
            'protocol': self.protocol,
            'occupancy': self.occupancy,
            'user_flag': self.user_flag,
            'reserved': self.reserved,
            'extra_data': self.extra_data,
            'enabled': self.enabled,
            'supports_enable_disable': self.supports_enable_disable,
        }

    def __repr__(self) -> str:
        """
        Returns string representation of the sensor.

        :return: String representation
        """
        return super().__repr__() + f"(name='{str(self.name)}'" \
            f' type={str(self.type)}' \
            f' subtype={str(self.subtype)}' \
            f' protocol={str(self.protocol)}' \
            f' occupancy={self.occupancy}' \
            f' user flag={str(self.user_flag)}' \
            f' reserved={str(self.reserved)}' \
            f" extra_data={str(self.extra_data)})"
