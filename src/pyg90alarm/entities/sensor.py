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
from ..definitions.base import (
    G90PeripheralDefinition,
    G90PeripheralProtocols, G90PeripheralTypes,
)
from ..definitions.sensors import (
    G90SensorDefinitions,
)
from ..const import G90Commands
from .base_entity import G90BaseEntity
from ..callback import G90CallbackList
from ..exceptions import G90PeripheralDefinitionNotFound
if TYPE_CHECKING:
    from ..alarm import (
        G90Alarm, SensorStateCallback, SensorLowBatteryCallback,
        SensorDoorOpenWhenArmingCallback, SensorTamperCallback,
    )


@dataclass
class G90SensorCommonData:  # pylint:disable=too-many-instance-attributes
    """
    Common protocol fields across read and write operations.

    :meta private:
    """
    parent_name: str
    index: int
    room_id: int
    type_id: int
    subtype: int
    timeout: int
    user_flags_data: int
    baudrate: int
    protocol_id: int
    reserved_data: int
    node_count: int


@dataclass
class G90SensorIncomingData(G90SensorCommonData):
    """
    Incoming (read operation) protocol fields.

    :meta private:
    """
    mask: int
    private_data: str


@dataclass
class G90SensorOutgoingData(G90SensorCommonData):
    """
    Outgoing (write operation) protocol fields.

    :meta private:
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
    # Flags that can be set by the user
    USER_SETTABLE = (
        ENABLED
        | ARM_DELAY
        | DETECT_DOOR
        | DOOR_CHIME
        | INDEPENDENT_ZONE
        | ALERT_WHEN_AWAY_AND_HOME
        | ALERT_WHEN_AWAY
    )


class G90SensorAlertModes(IntEnum):
    """
    Dedicated alert modes for the sensors (subset of user flags).
    """
    ALERT_ALWAYS = 0
    ALERT_WHEN_AWAY = 1
    ALERT_WHEN_AWAY_AND_HOME = 2


# Mapping of relevant user flags to alert modes
ALERT_MODES_MAP_BY_FLAG = {
    # No 'when away' or 'when away and home' flag set means 'alert always
    G90SensorUserFlags.NONE:
        G90SensorAlertModes.ALERT_ALWAYS,
    G90SensorUserFlags.ALERT_WHEN_AWAY:
        G90SensorAlertModes.ALERT_WHEN_AWAY,
    G90SensorUserFlags.ALERT_WHEN_AWAY_AND_HOME:
        G90SensorAlertModes.ALERT_WHEN_AWAY_AND_HOME,
}

# Reversed mapping of alert modes to corresponding user flags
ALERT_MODES_MAP_BY_VALUE = dict(
    zip(
        ALERT_MODES_MAP_BY_FLAG.values(),
        ALERT_MODES_MAP_BY_FLAG.keys()
    )
)


_LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-public-methods
class G90Sensor(G90BaseEntity):  # pylint:disable=too-many-instance-attributes
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
        self._state_callback: G90CallbackList[SensorStateCallback] = (
            G90CallbackList()
        )
        self._low_battery_callback: G90CallbackList[
            SensorLowBatteryCallback
        ] = G90CallbackList()
        self._low_battery = False
        self._tampered = False
        self._door_open_when_arming_callback: G90CallbackList[
            SensorDoorOpenWhenArmingCallback
        ] = G90CallbackList()
        self._tamper_callback: G90CallbackList[SensorTamperCallback] = (
            G90CallbackList()
        )
        self._door_open_when_arming = False
        self._proto_idx = proto_idx
        self._extra_data: Any = None
        self._unavailable = False
        self._definition: Optional[G90PeripheralDefinition] = None

    @property
    def definition(self) -> Optional[G90PeripheralDefinition]:
        """
        Returns the definition for the sensor.

        :return: Sensor definition
        """
        if not self._definition:
            # No definition has been cached, try to find it by type, subtype
            # and protocol
            try:
                self._definition = (
                    G90SensorDefinitions.get_by_id(
                        self.type, self.subtype, self.protocol
                    )
                )
            except G90PeripheralDefinitionNotFound:
                return None
        return self._definition

    def update(self, obj: G90Sensor) -> None:
        """
        Updates sensor from another instance.

        :param obj: Sensor instance to update from
        """
        self._protocol_data = obj.protocol_data
        self._proto_idx = obj.proto_idx

    @property
    def name(self) -> str:
        """
        Sensor name, accounting for multi-channel entities (single
        protocol entity results in multiple :class:`.G90Sensor` instances).

        :return: Sensor name
        """
        if self._protocol_data.node_count == 1:
            return self._protocol_data.parent_name
        return f'{self._protocol_data.parent_name}#{self._subindex + 1}'

    @property
    def _get_list_command(self) -> G90Commands:
        """
        Panel command used to refresh this entity.
        """
        return G90Commands.GETSENSORLIST

    @property
    def _set_single_command(self) -> G90Commands:
        """
        Panel command used to write this entity.
        """
        return G90Commands.SETSINGLESENSOR

    @property
    def _entity_kind(self) -> str:
        """
        Entity kind used for logging.
        """
        return 'sensor'

    @property
    def state_callback(self) -> G90CallbackList[SensorStateCallback]:
        """
        Callback that is invoked when the sensor changes its state.

        :return: Sensor state callback

        .. seealso:: :attr:`G90Alarm.sensor_callback` for compatiblity notes
        """
        return self._state_callback

    @state_callback.setter
    def state_callback(self, value: SensorStateCallback) -> None:
        self._state_callback.add(value)

    @property
    def low_battery_callback(
        self
    ) -> G90CallbackList[SensorLowBatteryCallback]:
        """
        Callback that is invoked when the sensor reports on low battery
        condition.

        :return: Sensor's low battery callback

        .. seealso:: :attr:`G90Alarm.sensor_callback` for compatiblity notes
        """
        return self._low_battery_callback

    @low_battery_callback.setter
    def low_battery_callback(self, value: SensorLowBatteryCallback) -> None:
        self._low_battery_callback.add(value)

    @property
    def door_open_when_arming_callback(
        self
    ) -> G90CallbackList[SensorDoorOpenWhenArmingCallback]:
        """
        Callback that is invoked when the sensor reports on open door
        condition when arming.

        :return: Sensor's door open when arming callback

        .. seealso:: :attr:`G90Alarm.sensor_callback` for compatiblity notes
        """
        return self._door_open_when_arming_callback

    @door_open_when_arming_callback.setter
    def door_open_when_arming_callback(
        self, value: SensorDoorOpenWhenArmingCallback
    ) -> None:
        self._door_open_when_arming_callback.add(value)

    @property
    def tamper_callback(self) -> G90CallbackList[SensorTamperCallback]:
        """
        Callback that is invoked when the sensor reports being tampered.

        :return: Sensor's tamper callback

        .. seealso:: :attr:`G90Alarm.sensor_callback` for compatiblity notes
        """
        return self._tamper_callback

    @tamper_callback.setter
    def tamper_callback(self, value: SensorTamperCallback) -> None:
        self._tamper_callback.add(value)

    @property
    def occupancy(self) -> bool:
        """
        Occupancy (occupied/not occupied, or triggered/not triggered)
        for the sensor.

        :return: Sensor occupancy
        """
        return self._occupancy

    def _set_occupancy(self, value: bool) -> None:
        """
        Sets occupancy state of the sensor.
        Intentionally private, as occupancy state is derived from
        notifications/alerts.

        :param value: Occupancy state
        """
        _LOGGER.debug(
            "Setting occupancy for sensor index=%s: '%s' %s"
            " (previous value: %s)",
            self.index, self.name, value, self._occupancy
        )
        self._occupancy = value

    @property
    def protocol(self) -> G90PeripheralProtocols:
        """
        Protocol type of the sensor.

        :return: Protocol type
        """
        return G90PeripheralProtocols(self._protocol_data.protocol_id)

    @property
    def type(self) -> G90PeripheralTypes:
        """
        Type of the sensor.

        :return: Sensor type
        """
        return G90PeripheralTypes(self._protocol_data.type_id)

    @property
    def subtype(self) -> int:
        """
        Sub-type of the sensor.

        :return: Sensor sub-type
        """
        return self._protocol_data.subtype

    @property
    def reserved(self) -> G90SensorReservedFlags:
        """
        Reserved flags (read/write mode) for the sensor.

        :return: Reserved flags
        """
        return G90SensorReservedFlags(self._protocol_data.reserved_data)

    @property
    def user_flag(self) -> G90SensorUserFlags:
        """
        User flags for the sensor, retained for compatibility - please use
        `:attr:user_flags` instead.

        :return: User flags
        """
        return self.user_flags

    @property
    def user_flags(self) -> G90SensorUserFlags:
        """
        User flags for the sensor (disabled/enabled, arming type etc).

        :return: User flags
        """
        return G90SensorUserFlags(self._protocol_data.user_flags_data)

    @property
    def node_count(self) -> int:
        """
        Number of nodes (channels) for the sensor.

        :return: Number of nodes
        """
        return self._protocol_data.node_count

    @property
    def parent(self) -> G90Alarm:
        """
        Parent instance of alarm panel class the sensor is associated
        with.

        :return: Parent instance
        """
        return self._parent

    @property
    def index(self) -> int:
        """
        Index (internal position) of the sensor in the alarm panel.

        :return: Internal sensor position
        """
        return self._protocol_data.index

    @property
    def subindex(self) -> int:
        """
        Index of the sensor within multi-node device.

        :return: Index of sensor in multi-node device.
        """
        return self._subindex

    @property
    def proto_idx(self) -> int:
        """
        Index of the sensor within list of sensors as retrieved from the alarm
        panel.

        :return: Index of sensor in list of sensors.
        """
        return self._proto_idx

    @property
    def type_name(self) -> Optional[str]:
        """
        Type of the sensor.

        :return: Type
        """
        if not self.definition:
            return None

        return self.definition.name

    @property
    def supports_updates(self) -> bool:
        """
        Indicates if the sensor supports updates.

        :return: Support for updates
        """
        if not self.definition:
            _LOGGER.debug(
                'Manipulating sensor at index=%s'
                ' is unsupported - no sensor definition for'
                ' type=%s, subtype=%s, protocol=%s',
                self.index, self.type, self.subtype, self.protocol
            )
            return False
        return True

    @property
    def supports_enable_disable(self) -> bool:
        """
        Indicates if disabling/enabling the sensor is supported.

        :return: Support for enabling/disabling the sensor
        """
        return self.supports_updates

    @property
    def protocol_data(self) -> G90SensorIncomingData:
        """
        Protocol data of the sensor.

        :return: Protocol data
        """
        return self._protocol_data

    @property
    def is_wireless(self) -> bool:
        """
        Indicates if the sensor is wireless.
        """
        return self.protocol not in (G90PeripheralProtocols.CORD,)

    @property
    def is_low_battery(self) -> bool:
        """
        Indicates if the sensor is reporting low battery.

        The condition is cleared when the sensor reports activity (i.e. is no
        longer low on battery as it is able to report the activity).
        """
        return self._low_battery

    def _set_low_battery(self, value: bool) -> None:
        """
        Sets low battery state of the sensor.

        Intentionally private, as low battery state is derived from
        notifications/alerts.

        :param value: Low battery state
        """
        _LOGGER.debug(
            "Setting low battery for sensor index=%s '%s': %s"
            " (previous value: %s)",
            self.index, self.name, value, self._low_battery
        )
        self._low_battery = value

    @property
    def is_tampered(self) -> bool:
        """
        Indicates if the sensor has been tampered.

        The condition is cleared when panel is armed/disarmed next time.
        """
        return self._tampered

    def _set_tampered(self, value: bool) -> None:
        """
        Sets tamper state of the sensor.

        Intentionally private, as tamper state is derived from
        notifications/alerts.

        :param value: Tamper state
        """
        _LOGGER.debug(
            "Setting tamper for sensor index=%s '%s': %s"
            " (previous value: %s)",
            self.index, self.name, value, self._tampered
        )
        self._tampered = value

    @property
    def is_door_open_when_arming(self) -> bool:
        """
        Indicates if the sensor reports on open door when arming.

        The condition is cleared when panel is armed/disarmed next time.
        """
        return self._door_open_when_arming

    def _set_door_open_when_arming(self, value: bool) -> None:
        """
        Sets door open state of the sensor when arming.

        Intentionally private, as door open state is derived from
        notifications/alerts.

        :param value: Door open state
        """
        _LOGGER.debug(
            "Setting door open when arming for sensor index=%s '%s': %s"
            " (previous value: %s)",
            self.index, self.name, value, self._door_open_when_arming
        )
        self._door_open_when_arming = value

    async def set_user_flag(self, value: G90SensorUserFlags) -> None:
        """
        Sets user flags of the sensor, retained for compatibility - please use
        `:meth:set_user_flags` instead.
        """
        await self.set_user_flags(value)

    async def set_user_flags(self, value: G90SensorUserFlags) -> None:
        """
        Sets user flags of the sensor.

        :param value: User flags to set, values other than
          :attr:`.G90SensorUserFlags.USER_SETTABLE` will be ignored and
          preserved from existing sensor flags.
        """
        if value & ~G90SensorUserFlags.USER_SETTABLE:
            _LOGGER.debug(
                'User flags for sensor index=%s contain non-user settable'
                ' flags, those will be ignored: %s',
                self.index, repr(value & ~G90SensorUserFlags.USER_SETTABLE)
            )

        await self._set_protocol_data(
            'set user flags',
            user_flags_data=(
                # Preserve flags that are not user-settable
                self.user_flags & ~G90SensorUserFlags.USER_SETTABLE
            ) | (
                # Combine them with the new user-settable flags
                value & G90SensorUserFlags.USER_SETTABLE
            )
        )

    async def set_name(self, value: str) -> None:
        """
        Sets sensor name on the panel.

        For multi-node entities the name is shared by all nodes on the panel;
        node suffixes are derived locally when the :attr:`name` is read.

        :param value: Name to set.
        """
        if self._protocol_data.parent_name == value:
            _LOGGER.debug(
                '%s index=%s: name %s has not changed, skipping update',
                self._entity_kind, self.index, repr(value)
            )
            return

        # Set the name refreshing the entities from panel once done - that
        # ensures the list of entities reflects recent changes
        await self._set_protocol_data(
            'set name', refresh_after_update=True, parent_name=value
        )

    async def _set_protocol_data(
        self, operation: str, refresh_after_update: bool = False,
        **updates: Any
    ) -> bool:
        """
        Updates protocol data on the panel.

        :param operation: Operation description for logging.
        :param refresh_after_update: Refresh cached entities from the panel
          after updating.
        :param updates: Protocol data fields to update.
        :return: True if the update has been sent to the panel.
        """
        if not self.supports_updates:
            return False

        # Checking private attribute directly, since `mypy` doesn't recognize
        # the check for sensor definition is done over `self.supports_updates`
        # property
        assert self.definition is not None

        # Refresh actual entity data from the alarm panel before modifying it.
        # This implies the entity is at the same position within protocol list
        # (`_proto_index`) as it has been read initially from the alarm panel
        # when instantiated.
        _LOGGER.debug(
            'Refreshing %s at index=%s, position in protocol list=%s',
            self._entity_kind, self.index, self.proto_idx
        )
        entities_result = self.parent.paginated_result(
            self._get_list_command,
            start=self.proto_idx, end=self.proto_idx
        )
        entities = [x.data async for x in entities_result]

        # Abort if entity is not found
        if not entities:
            _LOGGER.error(
                '%s index=%s not found when attempting to %s',
                self._entity_kind, self.index, operation
            )
            return False

        # Compare actual entity data from what the entity has been instantiated
        # from, and abort the operation if out-of-band changes are detected.
        actual_data = self._protocol_incoming_data_kls(*entities[0])
        if actual_data != self._protocol_data:
            _LOGGER.error(
                "%s index=%s '%s' has been changed externally,"
                " refusing to %s",
                self._entity_kind, self.index, self.name,
                operation
            )
            return False

        # Re-instantiate the protocol data with modified fields
        _data = asdict(actual_data)
        _data.update(updates)
        new_protocol_data = self._protocol_incoming_data_kls(**_data)

        if new_protocol_data == self._protocol_data:
            _LOGGER.debug(
                '%s index=%s: %s has not changed,'
                ' skipping update',
                self._entity_kind, self._protocol_data.index,
                operation
            )
            return False

        self._protocol_data = new_protocol_data

        # Generate protocol data from write operation, deriving values either
        # from fields read from the entity, or from the entity definition - not
        # all fields are present during read, only in definition.
        outgoing_data = self._protocol_outgoing_data_kls(
            parent_name=self._protocol_data.parent_name,
            index=self._protocol_data.index,
            room_id=self._protocol_data.room_id,
            type_id=self._protocol_data.type_id,
            subtype=self._protocol_data.subtype,
            timeout=self._protocol_data.timeout,
            user_flags_data=self._protocol_data.user_flags_data,
            baudrate=self._protocol_data.baudrate,
            protocol_id=self._protocol_data.protocol_id,
            reserved_data=self.definition.reserved_data,
            node_count=self._protocol_data.node_count,
            rx=self.definition.rx,
            tx=self.definition.tx,
            private_data=self.definition.private_data,
        )
        # Modify the entity
        await self._parent.command(
            self._set_single_command, list(astuple(outgoing_data))
        )

        # Refresh the entities from the panel if requested
        if refresh_after_update:
            await self._refresh_entities()

        return True

    async def _refresh_entities(self) -> None:
        """
        Refreshes cached entities from the panel.
        """
        await self.parent.get_sensors()

    def get_flag(self, flag: G90SensorUserFlags) -> bool:
        """
        Gets the user flag for the sensor.

        :param flag: User flag to get
        :return: User flag value
        """
        return flag in self.user_flag

    async def set_flag(
        self, flag: G90SensorUserFlags, value: bool
    ) -> None:
        """
        Sets the user flag for the sensor.

        :param flag: User flag to set
        :param value: New value for the user flag
        """
        # Skip updating the flag if it has the desired value
        if self.get_flag(flag) == value:
            _LOGGER.debug(
                'Sensor index=%s: user flag %s has not changed,'
                ' skipping update',
                self._protocol_data.index, repr(flag)
            )
            return

        # Invert corresponding user flag and set it
        user_flag = self.user_flag ^ flag
        await self.set_user_flag(user_flag)

    @property
    def enabled(self) -> bool:
        """
        Indicates if the sensor is enabled, using `:meth:get_user_flag` instead
        is preferred.

        :return: If sensor is enabled
        """
        return self.get_flag(G90SensorUserFlags.ENABLED)

    async def set_enabled(self, value: bool) -> None:
        """
        Sets the sensor enabled/disabled, using `:meth:set_user_flag` instead
        is preferred.

        :param value: New the sensor should be enabled
        """
        await self.set_flag(G90SensorUserFlags.ENABLED, value)

    @property
    def alert_mode(self) -> G90SensorAlertModes:
        """
        Alert mode for the sensor.

        :return: Alert mode
        """
        # Filter out irrelevant flags
        mode = self.user_flag & (
            G90SensorUserFlags.ALERT_WHEN_AWAY
            | G90SensorUserFlags.ALERT_WHEN_AWAY_AND_HOME
        )
        # Map the relevant user flags to alert mode
        result = ALERT_MODES_MAP_BY_FLAG.get(mode, None)

        if result is None:
            raise ValueError(
                f"Unknown alert mode for sensor {self.name}: {mode}"
                f" (user flag: {self.user_flag})"
            )

        return result

    async def set_alert_mode(self, value: G90SensorAlertModes) -> None:
        """
        Sets the sensor alert mode.
        """
        # Skip update if the value is already set to the requested one
        if self.alert_mode == value:
            _LOGGER.debug(
                'Sensor index=%s: alert mode %s has not changed,'
                ' skipping update',
                self._protocol_data.index, repr(value)
            )
            return

        # Map the alert mode to user flag value
        result = ALERT_MODES_MAP_BY_VALUE.get(value, None)

        if result is None:
            raise ValueError(
                f"Attempting to set alert mode for sensor {self.name} to"
                f" unknown value '{value}'"
            )

        # Add the mapped value over the user flags, filtering out previous
        # value of the alert mode
        user_flags = self.user_flag & ~(
            G90SensorUserFlags.ALERT_WHEN_AWAY
            | G90SensorUserFlags.ALERT_WHEN_AWAY_AND_HOME
        ) | result
        # Set the updated user flags
        await self.set_user_flags(user_flags)

    @property
    def extra_data(self) -> Any:
        """
        Extra data for the sensor, that can be used to store
        caller-specific information and will be carried by the sensor instance.
        """
        return self._extra_data

    @extra_data.setter
    def extra_data(self, val: Any) -> None:
        self._extra_data = val

    @property
    def is_unavailable(self) -> bool:
        """
        Indicates if the sensor is unavailable (e.g. has been removed).
        """
        return self._unavailable

    @is_unavailable.setter
    def is_unavailable(self, value: bool) -> None:
        self._unavailable = value

    async def delete(self) -> None:
        """
        Deletes the sensor from the alarm panel.
        """
        _LOGGER.debug("Deleting sensor: %s", self)

        # Mark the sensor as unavailable
        self.is_unavailable = True
        # Delete the sensor from the alarm panel
        await self.parent.command(
            G90Commands.DELSENSOR, [self.index]
        )

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
            'protocol_index': self.proto_idx,
            'subindex': self.subindex,
            'node_count': self.node_count,
            'protocol': self.protocol,
            'occupancy': self.occupancy,
            'user_flag': self.user_flag,
            'reserved': self.reserved,
            'extra_data': self.extra_data,
            'enabled': self.get_flag(G90SensorUserFlags.ENABLED),
            'detect_door': self.get_flag(G90SensorUserFlags.DETECT_DOOR),
            'door_chime': self.get_flag(G90SensorUserFlags.DOOR_CHIME),
            'independent_zone': self.get_flag(
                G90SensorUserFlags.INDEPENDENT_ZONE
            ),
            'arm_delay': self.get_flag(G90SensorUserFlags.ARM_DELAY),
            'alert_mode': self.alert_mode,
            'supports_updates': self.supports_updates,
            'is_wireless': self.is_wireless,
            'is_low_battery': self.is_low_battery,
            'is_tampered': self.is_tampered,
            'is_door_open_when_arming': self.is_door_open_when_arming,
            'is_unavailable': self.is_unavailable,
        }

    def __repr__(self) -> str:
        """
        Returns string representation of the sensor.

        :return: String representation
        """
        return super().__repr__() + f'({repr(self._asdict())})'

    def __eq__(self, value: object) -> bool:
        """
        Compares the sensor with another object.

        :param value: Object to compare with
        :return: If the sensor is equal to the object
        """
        if not isinstance(value, G90Sensor):
            return False

        return (
            self.type == value.type
            and self.subtype == value.subtype
            and self.protocol == value.protocol
            and self.index == value.index
            and self.subindex == value.subindex
        )
